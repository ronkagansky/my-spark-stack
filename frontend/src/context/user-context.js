'use client';

import { createContext, useContext, useEffect, useState } from 'react';
import { api } from '@/lib/api';
import { webSocketService } from '../lib/project-websocket';

const UserContext = createContext({
  user: null,
  projects: [],
  createAccount: async () => {},
  addProject: async () => {},
});

export function UserProvider({ children }) {
  const [user, setUser] = useState(null);
  const [projects, setProjects] = useState([]);

  useEffect(() => {
    if (localStorage.getItem('token')) {
      api.getCurrentUser().then(setUser);
      api.getUserProjects().then(setProjects);
    }
  }, []);

  const createAccount = async (username) => {
    const user = await api.createAccount(username);
    setUser(user);
    return user;
  };

  const addProject = (project) => {
    setProjects((prev) => [...prev, project]);
  };

  return (
    <UserContext.Provider
      value={{
        user,
        projects,
        createAccount,
        addProject,
      }}
    >
      {children}
    </UserContext.Provider>
  );
}

export const useUser = () => useContext(UserContext);
