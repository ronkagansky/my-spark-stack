'use client';

import { createContext, useContext, useEffect, useState } from 'react';
import { api } from '@/lib/api';
import { webSocketService } from '../lib/websocket';

const UserContext = createContext({
  user: null,
  createAccount: async () => {},
});

export function UserProvider({ children }) {
  const [user, setUser] = useState(null);

  useEffect(() => {
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

  useEffect(() => {
    if (user) {
      webSocketService.connect();
    }

    return () => {
      if (webSocketService.ws) {
        webSocketService.ws.close();
      }
    };
  }, [user]);

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
