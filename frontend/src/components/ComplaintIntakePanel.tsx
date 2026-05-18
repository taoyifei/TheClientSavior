import { Button, Checkbox, Input, InputNumber, Select, Space, Tooltip } from "antd";
import { AudioOutlined, ClearOutlined, ThunderboltOutlined } from "@ant-design/icons";
import type { CustomerProfile } from "../api/types";

type ComplaintIntakePanelProps = {
  complaint: string;
  profile: CustomerProfile;
  useLlm: boolean;
  loading: boolean;
  onComplaintChange: (value: string) => void;
  onProfileChange: (profile: CustomerProfile) => void;
  onUseLlmChange: (value: boolean) => void;
  onGenerate: () => void;
  onClear: () => void;
};

export default function ComplaintIntakePanel({
  complaint,
  profile,
  useLlm,
  loading,
  onComplaintChange,
  onProfileChange,
  onUseLlmChange,
  onGenerate,
  onClear
}: ComplaintIntakePanelProps) {
  const updateProfile = <K extends keyof CustomerProfile>(
    key: K,
    value: CustomerProfile[K]
  ) => {
    onProfileChange({ ...profile, [key]: value });
  };

  return (
    <section className="panel intake-panel">
      <div className="panel-header">
        <div>
          <h3>投诉录入与画像补充</h3>
          <p>粘贴客户原话，补充关键画像后生成可执行挽留方案。</p>
        </div>
      </div>

      <div className="intake-section">
        <div className="intake-title-row">
          <div className="intake-section-title">客户原话</div>
          <Tooltip title="开发中，敬请期待" placement="top">
            <Button
              aria-label="语音输入"
              className="voice-input-button"
              icon={<AudioOutlined />}
              shape="circle"
              type="text"
            />
          </Tooltip>
        </div>
        <Input.TextArea
          value={complaint}
          rows={7}
          placeholder="请粘贴客户原话，例如：这个套餐越来越贵，不行我就携号转网了。"
          onChange={(event) => onComplaintChange(event.target.value)}
        />
      </div>

      <div className="intake-section">
        <div className="intake-section-title">画像补充</div>
        <div className="form-grid">
          <label>
            当前月租
            <InputNumber
              min={0}
              value={profile.monthly_fee}
              addonAfter="元"
              onChange={(value) => updateProfile("monthly_fee", Number(value || 0))}
            />
          </label>
          <label>
            客户类型
            <Select
              value={profile.customer_type}
              options={["存量", "新入网", "高套", "家庭用户", "商客"].map((value) => ({
                label: value,
                value
              }))}
              onChange={(value) => updateProfile("customer_type", value)}
            />
          </label>
          <label>
            网龄
            <InputNumber
              min={0}
              value={profile.tenure_years}
              addonAfter="年"
              onChange={(value) => updateProfile("tenure_years", Number(value || 0))}
            />
          </label>
          <label>
            家庭号码数
            <InputNumber
              min={0}
              value={profile.family_mobile_count}
              addonAfter="个"
              onChange={(value) =>
                updateProfile("family_mobile_count", Number(value || 0))
              }
            />
          </label>
        </div>
        <div className="checkbox-grid">
          <Checkbox
            checked={profile.has_broadband}
            onChange={(event) =>
              updateProfile("has_broadband", event.target.checked)
            }
          >
            已有宽带
          </Checkbox>
          <Checkbox
            checked={profile.wants_device}
            onChange={(event) => updateProfile("wants_device", event.target.checked)}
          >
            有换机需求
          </Checkbox>
          <Checkbox
            checked={profile.wants_port_out}
            onChange={(event) =>
              updateProfile("wants_port_out", event.target.checked)
            }
          >
            明确携转/离网
          </Checkbox>
          <Checkbox checked={useLlm} onChange={(event) => onUseLlmChange(event.target.checked)}>
            启用云端模型
          </Checkbox>
        </div>
      </div>

      <div className="intake-section action-section">
        <div className="intake-section-title">生成操作</div>
        <Space direction="vertical" size={10} className="full-width">
          <Button
            block
            size="large"
            type="primary"
            icon={<ThunderboltOutlined />}
            loading={loading}
            onClick={onGenerate}
          >
            生成客户挽留方案
          </Button>
          <Button block type="text" icon={<ClearOutlined />} onClick={onClear}>
            清空输入，处理下一条
          </Button>
        </Space>
      </div>
    </section>
  );
}
