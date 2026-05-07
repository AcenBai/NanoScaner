import { useEffect, useState } from "react";
import { Alert, Button, Card, Descriptions, Space, Typography, message } from "antd";
import request from "../../api/request";

function ExportFeatures() {
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [errorMsg, setErrorMsg] = useState("");

  const loadSummary = async () => {
    setLoading(true);
    setErrorMsg("");
    try {
      const response = await request.get("/api/features/summary");
      setSummary(response.data);
    } catch (error) {
      const backendMessage =
        error?.response?.data?.detail || error?.message || "读取特征汇总失败";
      setErrorMsg(backendMessage);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadSummary();
  }, []);

  const exportFeatures = async () => {
    setExporting(true);
    try {
      const response = await request.get("/api/features/export", {
        responseType: "blob"
      });
      const blobUrl = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement("a");
      link.href = blobUrl;
      link.download = "extracted_features.csv";
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(blobUrl);
      message.success("特征导出成功");
    } catch (error) {
      const backendMessage =
        error?.response?.data?.detail || error?.message || "导出失败";
      message.error(backendMessage);
    } finally {
      setExporting(false);
    }
  };

  return (
    <Space direction="vertical" size="large" style={{ width: "100%" }}>
      <Card title="特征导出">
        <Space direction="vertical" style={{ width: "100%" }}>
          <Typography.Paragraph>
            当前导出的文件为 `backend/app/storage/features/extracted_features.csv`。请先在“特征提取”页面产生记录。
          </Typography.Paragraph>
          <Space>
            <Button onClick={loadSummary} loading={loading}>
              刷新汇总
            </Button>
            <Button type="primary" onClick={exportFeatures} loading={exporting} disabled={!summary?.exists}>
              导出 CSV
            </Button>
          </Space>
          {errorMsg && <Alert type="error" showIcon message={errorMsg} />}
        </Space>
      </Card>

      {summary && (
        <Card title="特征文件信息">
          <Descriptions bordered column={1} size="small">
            <Descriptions.Item label="exists">{String(summary.exists)}</Descriptions.Item>
            <Descriptions.Item label="rows">{summary.rows ?? 0}</Descriptions.Item>
            <Descriptions.Item label="path">{summary.path}</Descriptions.Item>
            <Descriptions.Item label="columns">{(summary.columns || []).join(", ")}</Descriptions.Item>
          </Descriptions>
        </Card>
      )}
    </Space>
  );
}

export default ExportFeatures;
