import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { LoginVerify } from "./LoginVerify";

const completeVerify = vi.fn().mockResolvedValue(undefined);
vi.mock("../lib/auth", () => ({
  useAuth: () => ({ completeVerify }),
}));
vi.mock("../lib/api", () => ({ api: { loginResend: vi.fn().mockResolvedValue(undefined) } }));

function renderAt(state: unknown) {
  return render(
    <MemoryRouter initialEntries={[{ pathname: "/login/verify", state }]}>
      <Routes>
        <Route path="/login/verify" element={<LoginVerify />} />
        <Route path="/dashboard" element={<div>DASH</div>} />
        <Route path="/login" element={<div>LOGIN</div>} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("LoginVerify", () => {
  it("redirects to /login when there is no challenge", () => {
    renderAt(undefined);
    expect(screen.getByText("LOGIN")).toBeInTheDocument();
  });

  it("submits the code and trust flag, then lands on dashboard", async () => {
    renderAt({ challengeToken: "c1", method: "email" });
    await userEvent.type(screen.getByLabelText(/code/i), "123456");
    await userEvent.click(screen.getByLabelText(/trust this device/i));
    await userEvent.click(screen.getByRole("button", { name: /verify/i }));
    expect(completeVerify).toHaveBeenCalledWith("c1", "123456", true);
    expect(await screen.findByText("DASH")).toBeInTheDocument();
  });
});
