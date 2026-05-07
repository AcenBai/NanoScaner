import { useEffect, useMemo, useState } from "react";
import { Alert, Button, Card, Descriptions, Input, Select, Space, Typography, message } from "antd";
import request from "../../api/request";

function ExtractFeatures() {
  const [signals, setSignals] = useState([]);
  const [loadingSignals, setLoadingSignals] = useState(false);
  const [extracting, setExtracting] = useState(false);
  const [selectedSignalUid, setSelectedSignalUid] = useState("");
  const [label, setLabel] = useState("");
  const [result, setResult] = useState(null);
  const [errorMsg, setErrorMsg] = useState("");

  useEffect(() => {
    const fetchProcessedSignals = async () => {
      setLoadingSignals(true);
      try {
        const response = await request.get("/api/features/processed-signals");
        setSignals(response.data?.signals || []);
      } catch (error) {
        const backendMessage =
          error?.response?.data?.detail || error?.message || "获取预处理信号失败";
        setErrorMsg(backendMessage);
      } finally {
        setLoadingSignals(false);
      }
    };

    fetchProcessedSignals();
  }, []);

  const selectedSignal = useMemo(
    () => signals.find((item) => item.signal_uid === selectedSignalUid),
    [signals, selectedSignalUid]
  );

  const runExtract = async () => {
    if (!selectedSignalUid) {
      message.error("请先选择预处理信号");
      return;
    }
    if (!label.trim()) {
      message.error("请填写 label");
      return;
    }

    setExtracting(true);
    setErrorMsg("");
    setResult(null);
    try {
      const response = await request.post("/api/features/extract", {
        signal_uid: selectedSignalUid,
        label: label.trim()
      });
      setResult(response.data);
      message.success("特征提取完成");
    } catch (error) {
      const backendMessage =
        error?.response?.data?.detail || error?.message || "特征提取失败";
      setErrorMsg(backendMessage);
      message.error(backendMessage);
    } finally {
      setExtracting(false);
    }
  };

  return (
    <Space direction="vertical" size="large" style={{ width: "100%" }}>
      <Card title="特征提取">
        <Space direction="vertical" style={{ width: "100%" }}>
          <Typography.Paragraph>
            从已预处理信号中提取特征。提取时必须选择 signal_uid 并填写 label；系统会根据正压/负压自动决定是否添加
            `_minus` 列后缀。
          </Typography.Paragraph>

          <Space wrap>
            <Select
              showSearch
              style={{ minWidth: 380 }}
              placeholder={loadingSignals ? "正在加载预处理信号..." : "请选择 signal_uid"}
              loading={loadingSignals}
              optionFilterProp="label"
              value={selectedSignalUid || undefined}
              onChange={setSelectedSignalUid}
              options={signals.map((item) => ({
                value: item.signal_uid,
                label: `${item.signal_uid} (${item.pressure_type || "unknown"})`
              }))}
            />
            <Input
              placeholder="请输入 label（例如：健康对照）"
              style={{ width: 280 }}
              value={label}
              onChange={(event) => setLabel(event.target.value)}
            />
            <Button type="primary" loading={extracting} onClick={runExtract}>
              开始提取
            </Button>
          </Space>

          {selectedSignal && (
            <Alert
              type="info"
              showIcon
              message={`当前信号：${selectedSignal.signal_uid}，pressure_type：${selectedSignal.pressure_type || "unknown"}`}
            />
          )}
          {errorMsg && <Alert type="error" showIcon message={errorMsg} />}
        </Space>
      </Card>

      {result && (
        <Card title="提取结果">
          <Descriptions bordered column={1} size="small">
            <Descriptions.Item label="signal_uid">{result.signal_uid}</Descriptions.Item>
            <Descriptions.Item label="label">{result.label}</Descriptions.Item>
            <Descriptions.Item label="pressure_type">{result.pressure_type}</Descriptions.Item>
            <Descriptions.Item label="feature_count">{result.feature_count}</Descriptions.Item>
            <Descriptions.Item label="saved_to">{result.saved_to}</Descriptions.Item>
            <Descriptions.Item label="status">{result.status}</Descriptions.Item>
          </Descriptions>
        </Card>
      )}
    </Space>
  );
}

export default ExtractFeatures;
