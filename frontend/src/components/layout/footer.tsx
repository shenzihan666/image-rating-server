/**
 * Footer component
 */
export function Footer() {
  return (
    <footer className="border-t bg-background">
      <div className="container flex h-16 items-center justify-between">
        <p className="text-sm text-muted-foreground">
          © {new Date().getFullYear()} Image Rating. All rights reserved.
        </p>
        <p className="text-sm text-muted-foreground">
          Built with FastAPI + Next.js + shadcn/ui
        </p>
      </div>
    </footer>
  );
}
