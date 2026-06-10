"use client";

import { create } from "zustand";
import type { UserResponse, LoginResponse } from "@samaa/shared";
import { toast } from "sonner";

interface AuthState {
  user: UserResponse | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (data: LoginResponse) => void;
  logout: () => void;
  hydrate: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  isAuthenticated: false,
  isLoading: true,

  login: (data: LoginResponse) => {
    localStorage.setItem("access_token", data.access_token);
    localStorage.setItem("refresh_token", data.refresh_token);
    localStorage.setItem("user", JSON.stringify(data.user));
    set({ user: data.user, isAuthenticated: true, isLoading: false });
  },

  logout: () => {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    localStorage.removeItem("user");
    set({ user: null, isAuthenticated: false, isLoading: false });
  },

  hydrate: () => {
    const stored = localStorage.getItem("user");
    const token = localStorage.getItem("access_token");
    if (stored && token) {
      try {
        const user = JSON.parse(stored) as UserResponse;
        set({ user, isAuthenticated: true, isLoading: false });
      } catch {
        set({ user: null, isAuthenticated: false, isLoading: false });
      }
    } else {
      set({ user: null, isAuthenticated: false, isLoading: false });
    }
    
    // Listen for session expired events
    if (typeof window !== "undefined") {
      window.addEventListener("session-expired", (e) => {
        const customEvent = e as CustomEvent<string>;
        set({ user: null, isAuthenticated: false, isLoading: false });
        toast.error("Session expired", {
          description: customEvent.detail,
          duration: 6000,
        });
      });
    }
  },
}));
