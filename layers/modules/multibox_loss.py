import paddle
import paddle.nn as nn
import paddle.nn.functional as F
from utils.box_utils import match, log_sum_exp
# from data import cfg_mnet
import numpy as np


class MultiBoxLoss(nn.Layer):
    """SSD Weighted Loss Function
    Compute Targets:
        1) Produce Confidence Target Indices by matching  ground truth boxes
           with (default) 'priorboxes' that have jaccard index > threshold parameter
           (default threshold: 0.5).
        2) Produce localization target by 'encoding' variance into offsets of ground
           truth boxes and their matched  'priorboxes'.
        3) Hard negative mining to filter the excessive number of negative examples
           that comes with using a large number of default bounding boxes.
           (default negative:positive ratio 3:1)
    Objective Loss:
        L(x,c,l,g) = (Lconf(x, c) + αLloc(x,l,g)) / N
        Where, Lconf is the CrossEntropy Loss and Lloc is the SmoothL1 Loss
        weighted by α which is set to 1 by cross val.
        Args:
            c: class confidences,
            l: predicted boxes,
            g: ground truth boxes
            N: number of matched default boxes
        See: https://arxiv.org/pdf/1512.02325.pdf for more details.
    """

    def __init__(self, num_classes, overlap_thresh, prior_for_matching, bkg_label, neg_mining, neg_pos, neg_overlap, encode_target):
        super(MultiBoxLoss, self).__init__()
        self.num_classes = num_classes
        self.threshold = overlap_thresh
        self.background_label = bkg_label
        self.encode_target = encode_target
        self.use_prior_for_matching = prior_for_matching
        self.do_neg_mining = neg_mining
        self.negpos_ratio = neg_pos
        self.neg_overlap = neg_overlap
        self.variance = [0.1, 0.2]

    def forward(self, predictions, priors, targets):
        """Multibox Loss
        Args:
            predictions (tuple): A tuple containing loc preds, conf preds,
            and prior boxes from SSD net.
                conf shape: tensor.size(batch_size,num_priors,num_classes)
                loc shape: tensor.size(batch_size,num_priors,4)
                priors shape: tensor.size(num_priors,4)

            ground_truth (tensor): Ground truth boxes and labels for a batch,
                shape: [batch_size,num_objs,5] (last idx is the label).
        """

        loc_data, conf_data, landm_data = predictions
        # priors = priors
        num = loc_data.shape[0]
        num_priors = priors.shape[0]

        # match priors (default boxes) and ground truth boxes
        loc_t = paddle.zeros([num, num_priors, 4])
        landm_t = paddle.zeros([num, num_priors, 10])
        conf_t = paddle.zeros([num, num_priors])
        for idx in range(num):
            truths = targets[idx][:, :4]
            labels = targets[idx][:, -1] #
            landms = targets[idx][:, 4:14]
            defaults = priors
            match(self.threshold, truths, defaults, self.variance, labels, landms, loc_t, conf_t, landm_t, idx)
            #self.threshold, truths, defaults, self.variance, labels, landms, loc_t, conf_t, landm_t, idx = 

        zeros = paddle.to_tensor(0,dtype='float32')
        pos1 = conf_t > zeros
        num_pos_landm = paddle.sum(paddle.to_tensor(pos1,dtype='float32'),axis=1, keepdim=True)
        N1 = max(paddle.sum(num_pos_landm),1)
        pos_idx1 = paddle.expand_as(pos1.unsqueeze(pos1.dim()),landm_data)
        if paddle.sum(paddle.to_tensor(pos_idx1,dtype='int64'))>0:
            landm_p = paddle.masked_select(landm_data,pos_idx1).reshape([-1,10])
            landm_t = paddle.masked_select(landm_t,pos_idx1).reshape([-1,10])
        else:
            landm_p = paddle.zeros([num, num_priors, 10])
            landm_p = landm_p.reshape([-1,10])
            landm_t = landm_t.reshape([-1,10])
        loss_landm = F.smooth_l1_loss(landm_p, landm_t, reduction='sum')


        pos = conf_t != zeros
        ones_map = paddle.ones_like(conf_t)
        conf_t = paddle.where(pos,ones_map,conf_t)
        pos_idx = paddle.expand_as(pos.unsqueeze(pos.dim()),loc_data)
        loc_p = paddle.masked_select(loc_data,pos_idx).reshape([-1, 4])
        loc_t =  paddle.masked_select(loc_t,pos_idx).reshape([-1, 4])
        loss_l = F.smooth_l1_loss(loc_p, loc_t, reduction='sum')

        # Compute max conf across batch for hard negative mining
        batch_conf = conf_data.reshape([-1, self.num_classes])
        index = conf_t.reshape([-1, 1])
        index_shape=index.shape[0]
        index = paddle.to_tensor(index,dtype = 'int64')
        index = paddle.squeeze(index).numpy()
        index_index = np.arange(index_shape)
        batch_conf  = batch_conf.numpy()
        gather_result = batch_conf[index_index,index]
        gather_result = paddle.to_tensor(gather_result).unsqueeze(1)
        batch_conf = paddle.to_tensor(batch_conf)
        loss_c = log_sum_exp(batch_conf) -gather_result #paddle.gather(batch_conf,1, index)

        # Hard Negative Mining
        #loss_c[pos.reshape([-1, 1])] = 0 # filter out pos boxes for now
        zeros_map = paddle.zeros_like(loss_c)
        loss_c = paddle.where(pos.reshape([-1, 1]),zeros_map,loss_c)
        loss_c = loss_c.reshape([num, -1])
        loss_idx = paddle.argsort(loss_c,axis=1, descending=True)
        idx_rank = paddle.argsort(loss_idx,axis=1)
        pos = paddle.to_tensor(pos,dtype='int64')
        num_pos = paddle.sum(pos,axis=1, keepdim=True)
        num_neg = paddle.clip(self.negpos_ratio*num_pos, max=pos.shape[1]-1)
        neg = idx_rank < paddle.expand_as(num_neg,idx_rank)
        neg = paddle.to_tensor(neg,dtype='int64')

        # Confidence Loss Including Positive and Negative Examples
        pos_idx = paddle.expand_as(pos.unsqueeze(2),conf_data)
        neg_idx = paddle.expand_as(neg.unsqueeze(2),conf_data)
        # gt()的转换
        #(pos_idx+neg_idx).gt(0)
        idx = (pos_idx+neg_idx) > 0
        conf_p = paddle.masked_select(conf_data,idx).reshape([-1,self.num_classes])
        idx = (pos+neg) > 0
        targets_weighted = paddle.masked_select(conf_t,idx)
        targets_weighted = paddle.to_tensor(targets_weighted,dtype = 'int64')
        loss_c = F.cross_entropy(conf_p, targets_weighted, reduction='sum')

        # Sum of losses: L(x,c,l,g) = (Lconf(x, c) + αLloc(x,l,g)) / N
        N = max(num_pos.sum(), 1)
        loss_l /= N
        loss_c /= N
        loss_landm /= N1

        return loss_l, loss_c, loss_landm
