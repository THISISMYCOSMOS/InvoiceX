import { Link } from "react-router-dom";

export function RoleSwitcher() {
  if (!import.meta.env.DEV) {
    return null;
  }

  return (
    <nav aria-label="개발 역할 전환">
      <Link to="/supplier">공급기업</Link>{" "}
      <Link to="/buyer">구매기업</Link>{" "}
      <Link to="/investor">투자기관</Link>{" "}
      <Link to="/dev/demo">데모 제어</Link>
    </nav>
  );
}
