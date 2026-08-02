import { ShellChrome } from "@/components/shell/shell-chrome";

export default function ShellLayout({ children }: { children: React.ReactNode }) {
  return <ShellChrome>{children}</ShellChrome>;
}
