import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ThemeToggle } from "./theme-toggle";

it("클릭 시 data-theme가 light↔dark 전환된다", async () => {
  document.documentElement.dataset.theme = "light";
  render(<ThemeToggle />);
  await userEvent.click(screen.getByRole("button", { name: /테마/ }));
  expect(document.documentElement.dataset.theme).toBe("dark");
  await userEvent.click(screen.getByRole("button", { name: /테마/ }));
  expect(document.documentElement.dataset.theme).toBe("light");
});
