import { Button, Card, Spinner } from "@darizae/marisma";

export function LoadingState({ label }: { label: string }) {
  return (
    <Card className="surface loading" role="status">
      <Spinner size="small" />
      <span>{label}</span>
    </Card>
  );
}

export function RetryButton({
  children,
  onClick,
}: {
  children: string;
  onClick: () => void;
}) {
  return (
    <Button type="button" variant="secondary" size="small" onClick={onClick}>
      {children}
    </Button>
  );
}
