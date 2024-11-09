'use client';

import { createContext, useContext, useEffect, useState } from 'react';
import { api } from '@/lib/api';

const UserContext = createContext({
  user: null,
  createAccount: async () => {},
  logout: () => {},
});

export function UserProvider({ children }) {
  const [user, setUser] = useState(null);

  useEffect(() => {
    // Load user on mount
    const username = localStorage.getItem('username');
    if (username) {
      api
        .getCurrentUser(username)
        .then(setUser)
        .catch(() => {
          localStorage.removeItem('username');
        });
    }
  }, []);

  const createAccount = async (username) => {
    const user = await api.createAccount(username);
    setUser(user);
    return user;
  };

  const logout = () => {
    localStorage.removeItem('username');
    setUser(null);
  };

  return (
    <UserContext.Provider value={{ user, createAccount, logout }}>
      {children}
    </UserContext.Provider>
  );
}

export const useUser = () => useContext(UserContext);
