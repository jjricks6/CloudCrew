import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export function BoardPage() {
  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold">Task Board</h2>
      <div className="grid gap-4 md:grid-cols-4">
        {["Backlog", "In Progress", "Review", "Done"].map((col) => (
          <Card key={col} className="min-h-[400px]">
            <CardHeader>
              <CardTitle className="text-sm font-medium">{col}</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground">
                Kanban board will be implemented in M5d.
              </p>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
