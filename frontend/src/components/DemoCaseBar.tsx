import { Button } from "antd";
import type { DemoCase } from "../api/types";

type DemoCaseBarProps = {
  demoCases: DemoCase[];
  onSelect: (demoCase: DemoCase) => void;
};

export default function DemoCaseBar({ demoCases, onSelect }: DemoCaseBarProps) {
  return (
    <div className="demo-chip-row">
      <span className="demo-label">演示号码</span>
      {demoCases.map((demoCase) => (
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
