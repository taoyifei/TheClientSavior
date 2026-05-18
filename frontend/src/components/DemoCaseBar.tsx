import { Button } from "antd";
import type { DemoCase } from "../api/types";

type DemoCaseBarProps = {
  demoCases: DemoCase[];
  onSelect: (demoCase: DemoCase) => void;
};

const HIDDEN_SCENE_KEYWORDS = ["宽带", "WiFi", "商户"];

export default function DemoCaseBar({ demoCases, onSelect }: DemoCaseBarProps) {
  const visibleCases = demoCases.filter(
    (demoCase) => !HIDDEN_SCENE_KEYWORDS.some((keyword) => demoCase.name.includes(keyword))
  );

  return (
    <div className="demo-chip-row">
      <span className="demo-label">热门场景</span>
      {visibleCases.map((demoCase) => (
        <Button
          key={demoCase.name}
          className="demo-chip"
          onClick={() => onSelect(demoCase)}
        >
          {demoCase.name}
        </Button>
      ))}
    </div>
  );
}
