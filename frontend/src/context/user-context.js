'use client';

import { createContext, useContext, useEffect, useState } from 'react';
import { api } from '@/lib/api';
import { webSocketService } from '../lib/project-websocket';

const UserContext = createContext({
  user: null,
  createAccount: async () => {},
});

export function UserProvider({ children }) {
  const [user, setUser] = useState(null);

  useEffect(() => {
    if (localStorage.getItem('token')) {
      api.getCurrentUser().then(setUser);
    }
  }, []);

  const createAccount = async (username) => {
    const user = await api.createAccount(username);
    setUser(user);
    return user;
  };

  return (
    <UserContext.Provider value={{ user, createAccount }}>
      {children}
    </UserContext.Provider>
  );
}

export const useUser = () => useContext(UserContext);
