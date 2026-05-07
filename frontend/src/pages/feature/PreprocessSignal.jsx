import { useEffect, useMemo, useState } from "react";
import { Alert, Button, Card, Select, Space, Spin, Typography, message } from "antd";
import request from "../../api/request";

function buildSvgPath(values, width, height, padding = 20) {
  if (!values || values.length === 0) {
    return "";
  }
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = max - min || 1;
  const stepX = (width - padding * 2) / Math.max(values.length - 1, 1);

  return values
    .map((value, index) => {
      const x = padding + index * stepX;
      const normalizedY = (value - min) / span;
      const y = height - padding - normalizedY * (height - padding * 2);
      return `${index === 0 ? "M" : "L"} ${x.toFixed(2)} ${y.toFixed(2)}`;
    })
    .join(" ");
}

function SignalLineChart({ title, values, color }) {
  const width = 760;
  const height = 260;
  const path = useMemo(() => buildSvgPath(values, width, height), [values]);

  return (
    <Card title={title}>
      {values?.length ? (
        <svg width="100%" viewBox={`0 0 ${width} ${height}`} role="img" aria-label={title}>
          <rect x="0" y="0" width={width} height={height} fill="#fafafa" />
          <path d={path} fill="none" stroke={color} strokeWidth="2" />
        </svg>
      ) : (
        <Typography.Text type="secondary">暂无数据</Typography.Text>
      )}
    </Card>
  );
}

function PreprocessSignal() {
  const [loadingSignals, setLoadingSignals] = useState(false);
  const [running, setRunning] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [signals, setSignals] = useState([]);
  const [selectedSignalUid, setSelectedSignalUid] = useState("");
  const [result, setResult] = useState(null);
  const [errorMsg, setErrorMsg] = useState("");

  useEffect(() => {
    const fetchSignals = async () => {
      setLoadingSignals(true);
      try {
        const response = await request.get("/api/preprocess/signals");
        setSignals(response.data?.signals || []);
      } catch (error) {
        const backendMessage =
          error?.response?.data?.detail || error?.message || "获取 signal_uid 失败";
        setErrorMsg(backendMessage);
      } finally {
        setLoadingSignals(false);
      }
    };

    fetchSignals();
  }, []);

  const runPreprocess = async () => {
    if (!selectedSignalUid) {
      message.error("请先选择 signal_uid");
      return;
    }
    setRunning(true);
    setErrorMsg("");
    setResult(null);
    try {
      const response = await request.post("/api/preprocess/run", {
        signal_uid: selectedSignalUid
      });
      setResult(response.data);
      message.success("预处理完成");
    } catch (error) {
      const backendMessage =
        error?.response?.data?.detail || error?.message || "预处理失败";
      setErrorMsg(backendMessage);
      message.error(backendMessage);
    } finally {
      setRunning(false);
    }
  };

  const exportProcessed = async () => {
    if (!selectedSignalUid) {
      message.error("请先选择 signal_uid");
      return;
    }
    setExporting(true);
    try {
      const response = await request.get(`/api/preprocess/export/${selectedSignalUid}`, {
        responseType: "blob"
      });
      const blobUrl = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement("a");
      link.href = blobUrl;
      link.download = `${selectedSignalUid}_processed.csv`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(blobUrl);
      message.success("导出成功");
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
      <Card title="信号预处理">
        <Space direction="vertical" style={{ width: "100%" }}>
          <Typography.Paragraph>
            选择已上传的 signal_uid，执行基线处理、滤波与归一化。页面展示原始信号和预处理信号的 400
            点可视化曲线，并支持导出处理结果。
          </Typography.Paragraph>
          <Space wrap>
            <Select
              showSearch
              style={{ minWidth: 360 }}
              placeholder={loadingSignals ? "正在加载 signal_uid..." : "请选择 signal_uid"}
              optionFilterProp="label"
              loading={loadingSignals}
              value={selectedSignalUid || undefined}
              onChange={setSelectedSignalUid}
              options={signals.map((item) => ({
                value: item.signal_uid,
                label: `${item.signal_uid} (${item.upload_time || "unknown"})`
              }))}
            />
            <Button type="primary" onClick={runPreprocess} loading={running}>
              执行预处理
            </Button>
            <Button onClick={exportProcessed} loading={exporting} disabled={!result}>
              导出预处理结果
            </Button>
          </Space>
          {!loadingSignals && signals.length === 0 && (
            <Alert type="warning" showIcon message="暂无已上传信号，请先在“原始信号上传”页面上传数据。" />
          )}
          {errorMsg && <Alert type="error" showIcon message={errorMsg} />}
        </Space>
      </Card>

      {running && (
        <Card>
          <Spin tip="正在执行预处理..." />
        </Card>
      )}

      {result && (
        <>
          <Card title="预处理结果">
            <Typography.Paragraph>
              signal_uid: {result.signal_uid}，原始点数: {result.num_raw_points}，处理后点数:{" "}
              {result.num_processed_points}
            </Typography.Paragraph>
          </Card>
          <SignalLineChart title="原始信号（采样 400 点）" values={result.raw_preview} color="#1677ff" />
          <SignalLineChart
            title="预处理后信号（采样 400 点）"
            values={result.processed_preview}
            color="#52c41a"
          />
        </>
      )}
    </Space>
  );
}

export default PreprocessSignal;
