/**
 * Header component
 */
import Link from "next/link";

export function Header() {
  return (
    <header className="sticky top-0 z-10 border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="container flex h-16 items-center justify-between">
        <Link href="/" className="flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary text-primary-foreground">
            <span className="text-sm font-bold">IR</span>
          </div>
          <span className="font-semibold">Image Rating</span>
        </Link>
        <nav className="flex items-center gap-6">
          <Link
            href="/login"
            className="text-sm font-medium text-muted-foreground hover:text-primary"
          >
            Sign In
          </Link>
          <Link
            href="/register"
            className="text-sm font-medium hover:text-primary"
          >
            Sign Up
          </Link>
        </nav>
      </div>
    </header>
  );
}
