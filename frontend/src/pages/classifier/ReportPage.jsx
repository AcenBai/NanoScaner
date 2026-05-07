import { useEffect, useState } from "react";
import { Alert, Button, Card, Descriptions, Select, Space, message } from "antd";
import request from "../../api/request";

function ReportPage() {
  const [models, setModels] = useState([]);
  const [runId, setRunId] = useState("");
  const [reportData, setReportData] = useState(null);
  const [errorMsg, setErrorMsg] = useState("");
  const [exporting, setExporting] = useState(false);

  const loadModels = async () => {
    try {
      const response = await request.get("/api/ml/models");
      const modelList = response.data?.models || [];
      setModels(modelList);
      if (!runId && modelList.length > 0) {
        setRunId(modelList[0].run_id);
      }
    } catch (error) {
      const backendMessage =
        error?.response?.data?.detail || error?.message || "读取模型列表失败";
      setErrorMsg(backendMessage);
    }
  };

  useEffect(() => {
    loadModels();
  }, []);

  useEffect(() => {
    if (!runId) return;
    const loadReport = async () => {
      try {
        const response = await request.get("/api/report/latest", { params: { run_id: runId } });
        setReportData(response.data);
      } catch (error) {
        const backendMessage =
          error?.response?.data?.detail || error?.message || "读取报告失败";
        setErrorMsg(backendMessage);
      }
    };
    loadReport();
  }, [runId]);

  const exportBundle = async () => {
    if (!runId) {
      message.error("请先选择 run_id");
      return;
    }
    setExporting(true);
    try {
      const response = await request.get("/api/report/export", {
        params: { run_id: runId },
        responseType: "blob"
      });
      const blobUrl = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement("a");
      link.href = blobUrl;
      link.download = `${runId}_report_bundle.zip`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(blobUrl);
      message.success("报告导出成功");
    } catch (error) {
      const backendMessage =
        error?.response?.data?.detail || error?.message || "导出报告失败";
      message.error(backendMessage);
    } finally {
      setExporting(false);
    }
  };

  return (
    <Space direction="vertical" size="large" style={{ width: "100%" }}>
      <Card title="报告生成">
        <Space direction="vertical" style={{ width: "100%" }}>
          <Select
            style={{ width: 360 }}
            value={runId || undefined}
            placeholder="请选择 run_id"
            onChange={setRunId}
            options={models.map((item) => ({
              value: item.run_id,
              label: `${item.run_id} (${item.created_at || "unknown"})`
            }))}
          />
          <Button type="primary" onClick={exportBundle} loading={exporting}>
            导出报告 ZIP
          </Button>
          {errorMsg && <Alert type="error" showIcon message={errorMsg} />}
        </Space>
      </Card>

      {reportData?.summary && (
        <Card title="报告摘要">
          <Descriptions bordered column={1} size="small">
            <Descriptions.Item label="run_id">{reportData.run_id}</Descriptions.Item>
            <Descriptions.Item label="created_at">{reportData.summary.created_at}</Descriptions.Item>
            <Descriptions.Item label="dataset_path">{reportData.summary.dataset_path}</Descriptions.Item>
            <Descriptions.Item label="bag_auc_soft">{reportData.summary.bag_auc_soft}</Descriptions.Item>
            <Descriptions.Item label="bag_accuracy_soft">{reportData.summary.bag_accuracy_soft}</Descriptions.Item>
            <Descriptions.Item label="sample_accuracy_hard">
              {reportData.summary.sample_accuracy_hard}
            </Descriptions.Item>
          </Descriptions>
        </Card>
      )}
    </Space>
  );
}

export default ReportPage;
