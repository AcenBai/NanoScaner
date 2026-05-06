import { Card, Typography } from "antd";

function PlaceholderPage({ title, description }) {
  return (
    <Card>
      <Typography.Title level={3}>{title}</Typography.Title>
      <Typography.Paragraph>{description}</Typography.Paragraph>
      <Typography.Text type="secondary">
        当前为项目骨架阶段，功能待后续实现。
      </Typography.Text>
    </Card>
  );
}

export default PlaceholderPage;
