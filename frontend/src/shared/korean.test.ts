import { expect, it } from "vitest";
import { withConditionalParticle, withTopicParticle } from "./korean";

it("받침이 없으면 는, 있으면 은, 한글이 아니면 는", () => {
  expect(withTopicParticle("카페")).toBe("카페는");
  expect(withTopicParticle("미용실")).toBe("미용실은");
  expect(withTopicParticle("PC방")).toBe("PC방은");
  expect(withTopicParticle("gym")).toBe("gym는");
});

it("받침이 없으면 라면, 있으면 이라면, 한글이 아니면 라면", () => {
  expect(withConditionalParticle("카페")).toBe("카페라면");
  expect(withConditionalParticle("한식")).toBe("한식이라면");
  expect(withConditionalParticle("gym")).toBe("gym라면");
});
