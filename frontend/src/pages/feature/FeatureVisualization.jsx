import { useEffect, useMemo, useState } from "react";
import { Alert, Button, Card, Col, Descriptions, Row, Space, Spin, Typography } from "antd";
import request from "../../api/request";

function valueToY(value, min, max, chartHeight, padding) {
  const span = max - min || 1;
  const normalized = (value - min) / span;
  return chartHeight - padding - normalized * (chartHeight - 2 * padding);
}

function BoxPlotCard({ title, stats }) {
  const width = 360;
  const height = 240;
  const padding = 26;

  const globalRange = useMemo(() => {
    if (!stats?.length) {
      return { min: 0, max: 1 };
    }
    return {
      min: Math.min(...stats.map((item) => item.min)),
      max: Math.max(...stats.map((item) => item.max))
    };
  }, [stats]);

  return (
    <Card title={title} size="small">
      {!stats?.length ? (
        <Typography.Text type="secondary">暂无可视化数据</Typography.Text>
      ) : (
        <svg width="100%" viewBox={`0 0 ${width} ${height}`} role="img" aria-label={title}>
          <rect x="0" y="0" width={width} height={height} fill="#fafafa" />
          {stats.map((item, index) => {
            const xCenter = 60 + index * 120;
            const boxWidth = 50;
            const yMin = valueToY(item.min, globalRange.min, globalRange.max, height, padding);
            const yQ1 = valueToY(item.q1, globalRange.min, globalRange.max, height, padding);
            const yMedian = valueToY(item.median, globalRange.min, globalRange.max, height, padding);
            const yQ3 = valueToY(item.q3, globalRange.min, globalRange.max, height, padding);
            const yMax = valueToY(item.max, globalRange.min, globalRange.max, height, padding);
            return (
              <g key={item.label}>
                <line x1={xCenter} y1={yMax} x2={xCenter} y2={yQ3} stroke="#666" />
                <line x1={xCenter} y1={yQ1} x2={xCenter} y2={yMin} stroke="#666" />
                <line x1={xCenter - 14} y1={yMax} x2={xCenter + 14} y2={yMax} stroke="#666" />
                <line x1={xCenter - 14} y1={yMin} x2={xCenter + 14} y2={yMin} stroke="#666" />
                <rect
                  x={xCenter - boxWidth / 2}
                  y={yQ3}
                  width={boxWidth}
                  height={Math.max(yQ1 - yQ3, 1)}
                  fill="#d6e4ff"
                  stroke="#1677ff"
                />
                <line x1={xCenter - boxWidth / 2} y1={yMedian} x2={xCenter + boxWidth / 2} y2={yMedian} stroke="#ff4d4f" />
                <text x={xCenter} y={height - 8} textAnchor="middle" fontSize="11">
                  {item.label}
                </text>
              </g>
            );
          })}
        </svg>
      )}
    </Card>
  );
}

function FeatureVisualization() {
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState("");
  const [data, setData] = useState(null);

  const loadData = async () => {
    setLoading(true);
    setErrorMsg("");
    try {
      const response = await request.get("/api/features/visualization/default");
      setData(response.data);
    } catch (error) {
      const backendMessage =
        error?.response?.data?.detail || error?.message || "读取默认特征库失败";
      setErrorMsg(backendMessage);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  return (
    <Space direction="vertical" size="large" style={{ width: "100%" }}>
      <Card title="默认特征库统计">
        <Space direction="vertical" style={{ width: "100%" }}>
          <Button onClick={loadData} loading={loading}>
            刷新默认特征库统计
          </Button>
          {loading && <Spin tip="正在加载统计..." />}
          {errorMsg && <Alert type="error" showIcon message={errorMsg} />}
          {data && (
            <>
              <Descriptions bordered column={1} size="small">
                <Descriptions.Item label="特征库路径">{data.library_path}</Descriptions.Item>
                <Descriptions.Item label="唯一样本数">{data.unique_sample_count}</Descriptions.Item>
                <Descriptions.Item label="label value_counts (按样本聚合)">
                  {Object.entries(data.label_value_counts_by_sample || {})
                    .map(([label, count]) => `${label}: ${count}`)
                    .join("；")}
                </Descriptions.Item>
              </Descriptions>
            </>
          )}
        </Space>
      </Card>

      {data && (
        <Row gutter={[16, 16]}>
          <Col xs={24} lg={12}>
            <BoxPlotCard title="peak_count（时域特征）" stats={data.boxplots?.peak_count || []} />
          </Col>
          <Col xs={24} lg={12}>
            <BoxPlotCard
              title="dominant_freq2_Wel（频域特征）"
              stats={data.boxplots?.dominant_freq2_Wel || []}
            />
          </Col>
          <Col xs={24} lg={12}>
            <BoxPlotCard
              title="wavelet_subband1（时频特征）"
              stats={data.boxplots?.wavelet_subband1 || []}
            />
          </Col>
          <Col xs={24} lg={12}>
            <BoxPlotCard
              title="hjorth_mobility（非线性特征）"
              stats={data.boxplots?.hjorth_mobility || []}
            />
          </Col>
        </Row>
      )}
    </Space>
  );
}

export default FeatureVisualization;
