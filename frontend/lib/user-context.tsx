"use client";

import { createContext, useContext, useState, useEffect } from "react";

interface User {
  id: string;
  display_name: string;
}

interface UserContextValue {
  user: User | null;
  userId: string;
}

const DEFAULT_USER: User = {
  id: process.env.NEXT_PUBLIC_DEFAULT_USER_ID ?? "df6f002d-c8c0-4d03-9298-1e58e8025a35",
  display_name: "Thiago",
};

const UserContext = createContext<UserContextValue>({
  user: DEFAULT_USER,
  userId: DEFAULT_USER.id,
});

export function UserProvider({ children }: { children: React.ReactNode }) {
  const [user] = useState<User>(DEFAULT_USER);

  return (
    <UserContext.Provider value={{ user, userId: user.id }}>
      {children}
    </UserContext.Provider>
  );
}

export function useUser(): UserContextValue {
  return useContext(UserContext);
}
