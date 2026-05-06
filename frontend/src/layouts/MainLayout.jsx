import { AppstoreOutlined, BarChartOutlined } from "@ant-design/icons";
import { Layout, Menu, Typography } from "antd";
import { Outlet, useLocation, useNavigate } from "react-router-dom";

const { Header, Sider, Content } = Layout;

const menuItems = [
  {
    key: "feature",
    icon: <AppstoreOutlined />,
    label: "特征提取分析",
    children: [
      { key: "/feature/upload-signal", label: "数据上传" },
      { key: "/feature/preprocess-signal", label: "信号预处理" },
      { key: "/feature/extract-features", label: "特征提取" },
      { key: "/feature/feature-visualization", label: "特征可视化" },
      { key: "/feature/export-features", label: "特征导出" }
    ]
  },
  {
    key: "classifier",
    icon: <BarChartOutlined />,
    label: "机器学习分类",
    children: [
      { key: "/classifier/upload-dataset", label: "特征表上传" },
      { key: "/classifier/train-model", label: "模型训练" },
      { key: "/classifier/model-evaluation", label: "模型评估" },
      { key: "/classifier/online-prediction", label: "在线预测" },
      { key: "/classifier/report", label: "报告生成" }
    ]
  }
];

function MainLayout() {
  const navigate = useNavigate();
  const location = useLocation();

  const selectedKey = location.pathname === "/" ? "/" : location.pathname;

  return (
    <Layout style={{ minHeight: "100vh" }}>
      <Sider width={260} theme="dark">
        <div style={{ color: "#fff", padding: "18px 16px", fontSize: 16 }}>
          Nanopore AI Platform
        </div>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[selectedKey]}
          items={[
            { key: "/", label: "Dashboard" },
            ...menuItems
          ]}
          onClick={({ key }) => navigate(key)}
        />
      </Sider>
      <Layout>
        <Header style={{ background: "#fff", padding: "0 24px" }}>
          <Typography.Title level={4} style={{ margin: "16px 0" }}>
            NanoScaner Demo
          </Typography.Title>
        </Header>
        <Content style={{ margin: 24 }}>
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  );
}

export default MainLayout;
