import { useState } from "react";
import {
  Alert,
  Button,
  Card,
  Descriptions,
  Form,
  Input,
  Select,
  Space,
  Typography,
  Upload,
  message
} from "antd";
import { UploadOutlined } from "@ant-design/icons";
import request from "../../api/request";

function UploadSignal() {
  const [form] = Form.useForm();
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState(null);
  const [errorMsg, setErrorMsg] = useState("");

  const handleSubmit = async (values) => {
    const fileObj = values.file?.[0]?.originFileObj;
    if (!fileObj) {
      message.error("请先选择文件。");
      return;
    }

    const formData = new FormData();
    formData.append("sample_name", values.sample_name);
    formData.append("sample_index", values.sample_index);
    formData.append("pressure_type", values.pressure_type);
    formData.append("file", fileObj);

    setUploading(true);
    setErrorMsg("");
    setResult(null);

    try {
      const response = await request.post("/api/signal/upload", formData, {
        headers: { "Content-Type": "multipart/form-data" }
      });
      setResult(response.data);
      message.success("上传成功");
    } catch (error) {
      const backendMessage =
        error?.response?.data?.detail || error?.message || "上传失败";
      setErrorMsg(backendMessage);
      message.error(backendMessage);
    } finally {
      setUploading(false);
    }
  };

  return (
    <Space direction="vertical" size="large" style={{ width: "100%" }}>
      <Card title="原始信号上传">
        <Space direction="vertical" size="middle" style={{ width: "100%" }}>
          <Typography.Paragraph>
            sample_uid = 样本名_序号，表示一个真实样本。signal_uid =
            样本名_序号_压力类型，表示某个样本在正压或负压条件下的一份信号文件。同一个
            sample_uid 可以同时拥有正压文件和负压文件。
          </Typography.Paragraph>

          <Form form={form} layout="vertical" onFinish={handleSubmit}>
            <Form.Item
              label="样本名 (sample_name)"
              name="sample_name"
              rules={[{ required: true, message: "请输入样本名" }]}
            >
              <Input placeholder="例如：PDAC001" />
            </Form.Item>

            <Form.Item
              label="样本序号 (sample_index)"
              name="sample_index"
              rules={[{ required: true, message: "请输入样本序号" }]}
            >
              <Input placeholder="例如：001" />
            </Form.Item>

            <Form.Item
              label="压力类型 (pressure_type)"
              name="pressure_type"
              rules={[{ required: true, message: "请选择压力类型" }]}
            >
              <Select
                placeholder="请选择压力类型"
                options={[
                  { label: "positive（正压文件）", value: "positive" },
                  { label: "negative（负压文件）", value: "negative" }
                ]}
              />
            </Form.Item>

            <Form.Item
              label="信号文件"
              name="file"
              valuePropName="fileList"
              getValueFromEvent={(event) =>
                Array.isArray(event) ? event : event?.fileList
              }
              rules={[{ required: true, message: "请上传 CSV、TXT 或 ABF 文件" }]}
            >
              <Upload
                beforeUpload={() => false}
                accept=".csv,.txt,.abf"
                maxCount={1}
              >
                <Button icon={<UploadOutlined />}>选择 CSV/TXT/ABF 文件</Button>
              </Upload>
            </Form.Item>

            <Form.Item>
              <Button type="primary" htmlType="submit" loading={uploading}>
                上传信号文件
              </Button>
            </Form.Item>
          </Form>

          {errorMsg && (
            <Alert
              type="error"
              showIcon
              message="上传失败"
              description={errorMsg}
            />
          )}
        </Space>
      </Card>

      {result && (
        <Card title="上传结果">
          <Descriptions bordered column={1} size="small">
            <Descriptions.Item label="signal_uid">{result.signal_uid}</Descriptions.Item>
            <Descriptions.Item label="sample_uid">{result.sample_uid}</Descriptions.Item>
            <Descriptions.Item label="sample_name">{result.sample_name}</Descriptions.Item>
            <Descriptions.Item label="sample_index">{result.sample_index}</Descriptions.Item>
            <Descriptions.Item label="pressure_label">{result.pressure_label}</Descriptions.Item>
            <Descriptions.Item label="original_filename">
              {result.original_filename}
            </Descriptions.Item>
            <Descriptions.Item label="saved_filename">
              {result.saved_filename}
            </Descriptions.Item>
            <Descriptions.Item label="num_points">{result.num_points}</Descriptions.Item>
            <Descriptions.Item label="upload_time">{result.upload_time}</Descriptions.Item>
            <Descriptions.Item label="status">{result.status}</Descriptions.Item>
          </Descriptions>
        </Card>
      )}
    </Space>
  );
}

export default UploadSignal;
