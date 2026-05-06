# Nanopore Current Signal AI Platform

本项目是一个本地运行的 demo 网站，不部署，不做登录，不使用数据库。

## 技术栈

- 后端：FastAPI
- 前端：React + Vite + Ant Design
- 图表：ECharts 或 Plotly
- 机器学习：scikit-learn + CatBoost
- 存储：本地 storage 文件夹

## 本地访问

- FastAPI: http://localhost:8000
- React: http://localhost:5173

## 系统结构

一个 React 前端平台，两个功能模块：

1. 特征提取分析模块
   - 数据上传
   - 信号预处理
   - 特征提取
   - 特征可视化
   - 特征导出

2. 机器学习分类模块
   - 特征表上传
   - 模型训练
   - 模型评估
   - 在线预测
   - 报告生成

一个 FastAPI 后端，负责：

- 文件上传
- 信号读取
- 信号预处理
- 特征提取
- 特征表保存
- CatBoost 模型训练
- 模型预测
- 报告生成

## 重要约束

- 第一版只做本地 demo。
- 不做 Docker。
- 不做 Nginx。
- 不做数据库。
- 不做登录权限。
- 不做 GPU 加速。
- 优先保证完整流程跑通。
- 同一个 bag_id 的 segment 不能同时出现在训练集和测试集。

## 重要参考
- /data4/baihexiang/NanoScaner/房水分辨率基线处理.ipynb这个文件是重要的参考文件，是主流程，包含了预处理特征提取与下游机器学习二分类的主流程（此文件没有相关特征分析或者可视化，以及下游预测报告。这些工程在其他文件里）