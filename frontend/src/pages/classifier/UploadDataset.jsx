import { useEffect, useState } from "react";
import { Alert, Button, Card, Descriptions, Space, Typography } from "antd";
import request from "../../api/request";

function UploadDataset() {
  const [loading, setLoading] = useState(false);
  const [summary, setSummary] = useState(null);
  const [errorMsg, setErrorMsg] = useState("");

  const loadSummary = async () => {
    setLoading(true);
    setErrorMsg("");
    try {
      const response = await request.get("/api/ml/dataset-summary");
      setSummary(response.data);
    } catch (error) {
      const backendMessage =
        error?.response?.data?.detail || error?.message || "读取默认特征库失败";
      setErrorMsg(backendMessage);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadSummary();
  }, []);

  return (
    <Space direction="vertical" size="large" style={{ width: "100%" }}>
      <Card title="默认训练特征库">
        <Space direction="vertical" style={{ width: "100%" }}>
          <Typography.Paragraph>
            机器学习训练阶段默认使用内置特征库，不需要手动上传数据集。
          </Typography.Paragraph>
          <Button onClick={loadSummary} loading={loading}>
            刷新默认特征库统计
          </Button>
          {errorMsg && <Alert type="error" showIcon message={errorMsg} />}
        </Space>
      </Card>

      {summary && (
        <Card title="数据集概览">
          <Descriptions bordered column={1} size="small">
            <Descriptions.Item label="dataset_path">{summary.dataset_path}</Descriptions.Item>
            <Descriptions.Item label="rows">{summary.rows}</Descriptions.Item>
            <Descriptions.Item label="unique_samples">{summary.unique_samples}</Descriptions.Item>
            <Descriptions.Item label="label_counts">
              {Object.entries(summary.label_counts || {})
                .map(([key, value]) => `${key}: ${value}`)
                .join("；")}
            </Descriptions.Item>
            <Descriptions.Item label="columns">{(summary.columns || []).join(", ")}</Descriptions.Item>
          </Descriptions>
        </Card>
      )}
    </Space>
  );
}

export default UploadDataset;
