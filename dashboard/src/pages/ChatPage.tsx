import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export function ChatPage() {
  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold">PM Chat</h2>
      <Card className="h-[calc(100vh-220px)]">
        <CardHeader>
          <CardTitle className="text-sm font-medium">
            Chat with the Project Manager
          </CardTitle>
        </CardHeader>
        <CardContent className="flex h-full items-center justify-center">
          <p className="text-muted-foreground">
            Chat interface will be implemented in M5c.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
