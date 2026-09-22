import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ThemeToggle } from "./theme-toggle";

it("클릭 시 data-theme가 light↔dark 전환되고 localStorage에 저장된다", async () => {
  localStorage.clear();
  document.documentElement.dataset.theme = "light";
  render(<ThemeToggle />);
  await userEvent.click(screen.getByRole("button", { name: /테마/ }));
  expect(document.documentElement.dataset.theme).toBe("dark");
  expect(localStorage.getItem("metabole-theme")).toBe("dark");
  await userEvent.click(screen.getByRole("button", { name: /테마/ }));
  expect(document.documentElement.dataset.theme).toBe("light");
  expect(localStorage.getItem("metabole-theme")).toBe("light");
});
