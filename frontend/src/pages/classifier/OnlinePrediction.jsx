import { useEffect, useState } from "react";
import { Alert, Button, Card, Descriptions, Input, Select, Space, Typography, message } from "antd";
import request from "../../api/request";

const EXAMPLE_JSON = `{
  "peak_count": 1000000,
  "peak_mean": 0.82
}`;

function OnlinePrediction() {
  const [models, setModels] = useState([]);
  const [signals, setSignals] = useState([]);
  const [runId, setRunId] = useState("");
  const [signalUid, setSignalUid] = useState("");
  const [featureJson, setFeatureJson] = useState("");
  const [predicting, setPredicting] = useState(false);
  const [result, setResult] = useState(null);
  const [errorMsg, setErrorMsg] = useState("");

  const loadInitialData = async () => {
    try {
      const [modelsResp, signalsResp] = await Promise.all([
        request.get("/api/ml/models"),
        request.get("/api/features/processed-signals")
      ]);
      const modelList = modelsResp.data?.models || [];
      setModels(modelList);
      if (modelList.length > 0) {
        setRunId(modelList[0].run_id);
      }
      setSignals(signalsResp.data?.signals || []);
    } catch (error) {
      const backendMessage =
        error?.response?.data?.detail || error?.message || "初始化在线预测页面失败";
      setErrorMsg(backendMessage);
    }
  };

  useEffect(() => {
    loadInitialData();
  }, []);

  const onPredict = async () => {
    if (!runId) {
      message.error("请先选择 run_id");
      return;
    }

    let parsedFeaturePayload = null;
    if (featureJson.trim()) {
      try {
        parsedFeaturePayload = JSON.parse(featureJson);
      } catch {
        message.error("特征 JSON 格式不正确");
        return;
      }
    }
    if (!signalUid && !parsedFeaturePayload) {
      message.error("请提供 signal_uid 或特征 JSON");
      return;
    }

    setPredicting(true);
    setErrorMsg("");
    setResult(null);
    try {
      const response = await request.post("/api/ml/predict", {
        run_id: runId,
        signal_uid: signalUid || null,
        feature_payload: parsedFeaturePayload
      });
      setResult(response.data);
      message.success("预测完成");
    } catch (error) {
      const backendMessage =
        error?.response?.data?.detail || error?.message || "预测失败";
      setErrorMsg(backendMessage);
      message.error(backendMessage);
    } finally {
      setPredicting(false);
    }
  };

  return (
    <Space direction="vertical" size="large" style={{ width: "100%" }}>
      <Card title="在线预测">
        <Space direction="vertical" style={{ width: "100%" }}>
          <Typography.Paragraph>
            第一步选择已训练模型 run_id；第二步提供 signal_uid 或手动输入特征 JSON 执行预测。
          </Typography.Paragraph>
          <Select
            style={{ width: 400 }}
            value={runId || undefined}
            placeholder="请选择 run_id"
            onChange={setRunId}
            options={models.map((item) => ({
              value: item.run_id,
              label: `${item.run_id} (${item.created_at || "unknown"})`
            }))}
          />
          <Select
            allowClear
            style={{ width: 400 }}
            value={signalUid || undefined}
            placeholder="可选：选择 signal_uid（将自动提特征）"
            onChange={(value) => setSignalUid(value || "")}
            options={signals.map((item) => ({
              value: item.signal_uid,
              label: item.signal_uid
            }))}
          />
          <Input.TextArea
            rows={8}
            value={featureJson}
            onChange={(event) => setFeatureJson(event.target.value)}
            placeholder={EXAMPLE_JSON}
          />
          <Button type="primary" loading={predicting} onClick={onPredict}>
            执行预测
          </Button>
          {errorMsg && <Alert type="error" showIcon message={errorMsg} />}
        </Space>
      </Card>

      {result && (
        <Card title="预测结果">
          <Descriptions bordered column={1} size="small">
            <Descriptions.Item label="run_id">{result.run_id}</Descriptions.Item>
            <Descriptions.Item label="signal_uid">{result.signal_uid || "-"}</Descriptions.Item>
            <Descriptions.Item label="pred_index">{result.pred_index}</Descriptions.Item>
            <Descriptions.Item label="pred_label">{result.pred_label}</Descriptions.Item>
            <Descriptions.Item label="probabilities">
              {(result.probabilities || []).join(", ")}
            </Descriptions.Item>
            <Descriptions.Item label="status">{result.status}</Descriptions.Item>
          </Descriptions>
        </Card>
      )}
    </Space>
  );
}

export default OnlinePrediction;
