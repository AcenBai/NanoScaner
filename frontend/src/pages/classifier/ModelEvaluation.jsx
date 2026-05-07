import { useEffect, useState } from "react";
import { Alert, Card, Col, Descriptions, Row, Select, Space, Typography } from "antd";
import request from "../../api/request";

function ModelEvaluation() {
  const [models, setModels] = useState([]);
  const [runId, setRunId] = useState("");
  const [evaluation, setEvaluation] = useState(null);
  const [errorMsg, setErrorMsg] = useState("");

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
    const loadEvaluation = async () => {
      setErrorMsg("");
      try {
        const response = await request.get("/api/ml/evaluation", {
          params: { run_id: runId }
        });
        setEvaluation(response.data);
      } catch (error) {
        const backendMessage =
          error?.response?.data?.detail || error?.message || "读取评估结果失败";
        setErrorMsg(backendMessage);
      }
    };
    loadEvaluation();
  }, [runId]);

  const metrics = evaluation?.metrics?.metrics;
  const bag = metrics?.bag;
  const sample = metrics?.sample;

  return (
    <Space direction="vertical" size="large" style={{ width: "100%" }}>
      <Card title="模型评估">
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
          {errorMsg && <Alert type="error" showIcon message={errorMsg} />}
        </Space>
      </Card>

      {evaluation && (
        <>
          <Card title="核心指标">
            <Descriptions bordered column={1} size="small">
              <Descriptions.Item label="run_id">{evaluation.run_id}</Descriptions.Item>
              <Descriptions.Item label="bag_auc_soft">{bag?.auc_soft}</Descriptions.Item>
              <Descriptions.Item label="bag_accuracy_soft">{bag?.accuracy_soft}</Descriptions.Item>
              <Descriptions.Item label="sample_accuracy_hard">{sample?.accuracy_hard}</Descriptions.Item>
            </Descriptions>
          </Card>

          <Row gutter={[16, 16]}>
            <Col xs={24} lg={12}>
              <Card title="ROC (test)">
                <img
                  alt="roc"
                  style={{ width: "100%" }}
                  src={`/api/report/file?run_id=${encodeURIComponent(runId)}&name=roc_test.png`}
                />
              </Card>
            </Col>
            <Col xs={24} lg={12}>
              <Card title="Confusion Matrix">
                <img
                  alt="confusion"
                  style={{ width: "100%" }}
                  src={`/api/report/file?run_id=${encodeURIComponent(runId)}&name=confusion_matrix_bag.png`}
                />
              </Card>
            </Col>
            <Col xs={24} lg={12}>
              <Card title="Radar Metrics">
                <img
                  alt="radar"
                  style={{ width: "100%" }}
                  src={`/api/report/file?run_id=${encodeURIComponent(runId)}&name=radar_metrics.png`}
                />
              </Card>
            </Col>
            <Col xs={24} lg={12}>
              <Card title="Top15 Feature Importance">
                <img
                  alt="feature-importance"
                  style={{ width: "100%" }}
                  src={`/api/report/file?run_id=${encodeURIComponent(runId)}&name=feature_importance_top15.png`}
                />
              </Card>
            </Col>
          </Row>
          <Typography.Text type="secondary">
            说明：图表风格与导出结构参考 notebook 产物，当前在后端自动落盘后由本页读取展示。
          </Typography.Text>
        </>
      )}
    </Space>
  );
}

export default ModelEvaluation;
