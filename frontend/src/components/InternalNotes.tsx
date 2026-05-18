type InternalNotesProps = {
  notes: string[];
};

export default function InternalNotes({ notes }: InternalNotesProps) {
  if (!notes.length) return null;

  return (
    <section className="panel subtle">
      <div className="panel-header">
        <div>
          <h3>内部提醒</h3>
          <p>办理前需要客服核查的系统事项。</p>
        </div>
      </div>
      <ul className="note-list">
        {notes.map((note) => (
          <li key={note}>{note}</li>
        ))}
      </ul>
    </section>
  );
}
