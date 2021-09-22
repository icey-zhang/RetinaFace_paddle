# RetinaFace_paddle
RetinaFace in Paddle
## 一、简介
本项目采用百度飞桨框架paddlepaddle复现：RetinaFace: Single-stage Dense Face Localisation in the Wild, by Jiaqing Zhang (张佳青)

paper：[RetinaFace: Single-stage Dense Face Localisation in the Wild](https://arxiv.org/pdf/1905.00641v2.pdf)

code：[RetinaFace](https://github.com/deepinsight/insightface/blob/master/detection/retinaface/README.md)

本代码参考 [Pytorch_Retinaface](https://github.com/biubug6/Pytorch_Retinaface)，致敬开源精神，respect！

## 二、复现结果

本代码只复现论文的Table3，数据集为widerface，backbone为resnet50

|Method |Easy |Medium |Hard |mAP|
|  ----  |  ----  |  ----  |  ----  |----  |
|FPN+Context |95.532 |95.134 |90.714 |50.842|
|+DCN |96.349 |95.833 |91.286 |51.522|
|+Lpts |96.467 |96.075 |91.694 |52.297|
|+Lpixel |96.413 |95.864 |91.276 |51.492|
|+Lpts + Lpixel |96.942 |96.175 |91.857 |52.318|
|复现 |94.380 |92.521 |76.704 |57.508|

<img src=https://github.com/icey-zhang/RetinaFace_paddle/blob/main/process/333.jpg width=50% />

## 三、环境依赖

Paddle 2.1.2

## 四、实现

### 训练

#### 下载数据集

1. 下载WIDERFACE数据集
  
[下载链接aistudio](https://aistudio.baidu.com/aistudio/datasetdetail/104236)

```
  /widerface/
    train/
      images/
      label.txt
    val/
      images/
      wider_val.txt
```

#### 开始训练

```
CUDA_VISIBLE_DEVICES=0 python train.py --training_dataset /home/aistudio/widerface/train/label.txt
```

权重保存在./weights目录下

### 测试

#### 下载权重

40epoch即可，70epoch更佳

[weights](https://pan.baidu.com/s/1nq9CufWCeX4hCxR2JgY3mg) 提取码：y86z。

权重保存在./weights目录下

#### 生成txt文件

```
CUDA_VISIBLE_DEVICES=0 python test_widerface.py --dataset_folder /home/aistudio/widerface/val/images/  --trained_model /home/aistudio/RetinaFace-paddle/weights/Resnet50_epoch_40.pdparams --save_image
```
save_image为可视化检测结果
请使用V100进行测试
#### 评估txt文件
```
cd ./widerface_evaluate
python setup.py build_ext --inplace
python evaluation.py
```
记得修改evaluation主函数txt文件的目录

## 五、代码结构


```
./RetinaFace_paddle
├─models               #模型
├─data                 #数据集相关的API和网络的config   
├─utils                #预测框相关的API  
├─layers               #预测框相关的API
├─weights              #权重
├─results              #可视化结果
├─widerface_evaluate   #评估工具包
|  README.md                               
│  train.py            #训练
│  test_widerface.py   #测试

```

## 六、模型信息

|  信息   |  说明 |
|  ----  |  ----  |
| 作者 | 张佳青 |
| 时间 | 2021.09 |
| 框架版本 | Paddle 2.1.2 |
| 应用场景 | 人脸检测 |
| 模型权重 | [weights](https://pan.baidu.com/s/1nq9CufWCeX4hCxR2JgY3mg) 提取码：y86z |
| 飞桨项目 | [欢迎fork](https://aistudio.baidu.com/aistudio/projectdetail/2357312?contributionType=1) |
|  数据集  | [下载链接aistudio](https://aistudio.baidu.com/aistudio/datasetdetail/104236) |
