import { InboxOutlined } from "@ant-design/icons";

type EmptyStateProps = {
  title: string;
  body: string;
};

export default function EmptyState({ title, body }: EmptyStateProps) {
  return (
    <div className="empty-state">
      <InboxOutlined className="empty-icon" />
      <h3>{title}</h3>
      <p>{body}</p>
    </div>
  );
}
