import { useEffect, useState } from "react";
import { Alert, Card, Space, Typography } from "antd";
import request from "../api/request";

function Dashboard() {
  const [status, setStatus] = useState("loading");

  useEffect(() => {
    let mounted = true;

    request
      .get("/health")
      .then(() => {
        if (mounted) {
          setStatus("success");
        }
      })
      .catch(() => {
        if (mounted) {
          setStatus("error");
        }
      });

    return () => {
      mounted = false;
    };
  }, []);

  return (
    <Card>
      <Space direction="vertical" size="middle" style={{ width: "100%" }}>
        <Typography.Title level={3}>Dashboard</Typography.Title>
        <Typography.Paragraph>
          本页面用于检查系统连通性与查看平台概览。
        </Typography.Paragraph>
        {status === "loading" && <Alert type="info" message="正在检查后端连接..." />}
        {status === "success" && (
          <Alert type="success" message="后端连接成功" showIcon />
        )}
        {status === "error" && (
          <Alert type="error" message="后端连接失败" showIcon />
        )}
      </Space>
    </Card>
  );
}

export default Dashboard;
