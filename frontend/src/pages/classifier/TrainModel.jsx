import { useEffect, useState } from "react";
import { Alert, Button, Card, Descriptions, Form, InputNumber, Select, Space, Typography, message } from "antd";
import request from "../../api/request";

function TrainModel() {
  const [form] = Form.useForm();
  const [training, setTraining] = useState(false);
  const [result, setResult] = useState(null);
  const [models, setModels] = useState([]);
  const [datasetSummary, setDatasetSummary] = useState(null);
  const [errorMsg, setErrorMsg] = useState("");

  const loadModels = async () => {
    try {
      const response = await request.get("/api/ml/models");
      setModels(response.data?.models || []);
    } catch (error) {
      const backendMessage =
        error?.response?.data?.detail || error?.message || "读取模型列表失败";
      setErrorMsg(backendMessage);
    }
  };

  useEffect(() => {
    form.setFieldsValue({
      n_splits: 10,
      iterations: 2000,
      learning_rate: 0.05,
      depth: 8,
      l2_leaf_reg: 1,
      random_seed: 2018
    });
    request
      .get("/api/ml/dataset-summary")
      .then((response) => setDatasetSummary(response.data))
      .catch(() => {});
    loadModels();
  }, []);

  const onTrain = async (values) => {
    setTraining(true);
    setErrorMsg("");
    setResult(null);
    try {
      const response = await request.post("/api/ml/train", values);
      setResult(response.data);
      message.success("训练完成");
      loadModels();
    } catch (error) {
      const backendMessage =
        error?.response?.data?.detail || error?.message || "训练失败";
      setErrorMsg(backendMessage);
      message.error(backendMessage);
    } finally {
      setTraining(false);
    }
  };

  return (
    <Space direction="vertical" size="large" style={{ width: "100%" }}>
      <Card title="模型训练">
        <Space direction="vertical" style={{ width: "100%" }}>
          <Typography.Paragraph>训练源固定为默认特征库 `df_feature_default.csv`。</Typography.Paragraph>
          <Form form={form} layout="vertical" onFinish={onTrain}>
            <Form.Item label="negative_label（可选）" name="negative_label">
              <Select
                allowClear
                placeholder="默认自动推断（优先 健康对照 vs 其他疾病）"
                options={(datasetSummary?.unique_labels || []).map((label) => ({
                  label,
                  value: label
                }))}
              />
            </Form.Item>
            <Form.Item label="positive_label（可选）" name="positive_label">
              <Select
                allowClear
                placeholder="默认自动推断"
                options={(datasetSummary?.unique_labels || []).map((label) => ({
                  label,
                  value: label
                }))}
              />
            </Form.Item>
            <Form.Item label="GroupKFold 折数" name="n_splits">
              <InputNumber min={2} max={20} />
            </Form.Item>
            <Form.Item label="iterations" name="iterations">
              <InputNumber min={10} max={10000} />
            </Form.Item>
            <Form.Item label="learning_rate" name="learning_rate">
              <InputNumber min={0.001} max={1} step={0.001} />
            </Form.Item>
            <Form.Item label="depth" name="depth">
              <InputNumber min={2} max={12} />
            </Form.Item>
            <Form.Item label="l2_leaf_reg" name="l2_leaf_reg">
              <InputNumber min={0.01} max={100} step={0.01} />
            </Form.Item>
            <Form.Item label="random_seed" name="random_seed">
              <InputNumber min={0} />
            </Form.Item>
            <Form.Item>
              <Button type="primary" htmlType="submit" loading={training}>
                开始训练
              </Button>
            </Form.Item>
          </Form>
          {errorMsg && <Alert type="error" showIcon message={errorMsg} />}
        </Space>
      </Card>

      {result && (
        <Card title="训练结果">
          <Descriptions bordered column={1} size="small">
            <Descriptions.Item label="run_id">{result.run_id}</Descriptions.Item>
            <Descriptions.Item label="model_path">{result.model_path}</Descriptions.Item>
            <Descriptions.Item label="metrics_path">{result.metrics_path}</Descriptions.Item>
            <Descriptions.Item label="bag_auc_soft">{result.summary?.bag_auc_soft}</Descriptions.Item>
            <Descriptions.Item label="bag_accuracy_soft">{result.summary?.bag_accuracy_soft}</Descriptions.Item>
            <Descriptions.Item label="sample_accuracy_hard">{result.summary?.sample_accuracy_hard}</Descriptions.Item>
          </Descriptions>
        </Card>
      )}

      <Card title="已训练模型">
        <Descriptions bordered column={1} size="small">
          <Descriptions.Item label="count">{models.length}</Descriptions.Item>
          <Descriptions.Item label="run_ids">
            {models.map((item) => item.run_id).join(", ")}
          </Descriptions.Item>
        </Descriptions>
      </Card>
    </Space>
  );
}

export default TrainModel;
