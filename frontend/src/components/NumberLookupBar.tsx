import { Button, Input, message } from "antd";
import { ClearOutlined, SearchOutlined } from "@ant-design/icons";
import { getErrorMessage } from "../api/client";
import type { CustomerLookupResponse } from "../api/types";

type NumberLookupBarProps = {
  phone: string;
  lookupStatus: string;
  loading?: boolean;
  onPhoneChange: (value: string) => void;
  onLookup: () => Promise<CustomerLookupResponse | void>;
  onClear: () => void;
  onTestLLM: () => Promise<void>;
};

export default function NumberLookupBar({
  phone,
  lookupStatus,
  loading,
  onPhoneChange,
  onLookup,
  onClear,
  onTestLLM
}: NumberLookupBarProps) {
  const handleLookup = async () => {
    try {
      await onLookup();
    } catch (error) {
      message.error(getErrorMessage(error));
    }
  };

  return (
    <section className="command-bar">
      <div>
        <div className="command-title">号码查询</div>
        <div className="command-subtitle">
          输入客户手机号，优先查询本地演示画像；若本次已处理过，将从风险看板记录回填画像。手机号仅用于本地看板，不传入模型。
        </div>
      </div>
      <div className="lookup-row">
        <Input
          size="large"
          value={phone}
          onChange={(event) => onPhoneChange(event.target.value)}
          placeholder="请输入 11 位手机号，例如 13800138001"
          onPressEnter={handleLookup}
        />
        <Button
          size="large"
          type="primary"
          icon={<SearchOutlined />}
          loading={loading}
          onClick={handleLookup}
        >
          查询客户
        </Button>
        <Button size="large" icon={<ClearOutlined />} onClick={onClear}>
          清空
        </Button>
        <Button size="large" onClick={onTestLLM}>
          LLM 测试
        </Button>
      </div>
      {lookupStatus && <div className="lookup-status">{lookupStatus}</div>}
    </section>
  );
}
