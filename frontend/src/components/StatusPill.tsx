type StatusPillProps = {
  label: string;
  value?: string | number;
  tone?: "blue" | "green" | "orange" | "red" | "gray";
};

export default function StatusPill({
  label,
  value,
  tone = "blue"
}: StatusPillProps) {
  return (
    <span className={`status-pill ${tone}`}>
      <span>{label}</span>
      {value !== undefined && <strong>{value}</strong>}
    </span>
  );
}
