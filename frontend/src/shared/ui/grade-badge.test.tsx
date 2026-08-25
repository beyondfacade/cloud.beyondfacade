import { render, screen } from "@testing-library/react";
import { GradeBadge } from "./grade-badge";

it("fact는 '확인된 사실', signal은 '참고 신호' 라벨", () => {
  render(<><GradeBadge grade="fact" /><GradeBadge grade="signal" /></>);
  expect(screen.getByText("확인된 사실")).toBeInTheDocument();
  expect(screen.getByText("참고 신호")).toBeInTheDocument();
});
