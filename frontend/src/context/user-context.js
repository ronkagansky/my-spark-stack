'use client';

import { createContext, useContext, useEffect, useState } from 'react';
import { api } from '@/lib/api';
import { webSocketService } from '../lib/project-websocket';

const UserContext = createContext({
  user: null,
  team: null,
  teams: [],
  chats: [],
  createAccount: async () => {},
  addChat: async () => {},
});

export function UserProvider({ children }) {
  const [user, setUser] = useState(null);
  const [chats, setChats] = useState([]);
  const [teams, setTeams] = useState([]);
  const [team, setTeam] = useState(null);

  useEffect(() => {
    if (localStorage.getItem('token')) {
      api.getCurrentUser().then(setUser);
      api.getChats().then(setChats);
      api.getTeams().then((teams) => {
        setTeams(teams);
        if (!localStorage.getItem('team')) {
          setTeam(teams[0]);
          localStorage.setItem('team', teams[0].id);
        } else {
          setTeam(
            teams.find((t) => t.id + '' === localStorage.getItem('team'))
          );
        }
      });
    }
  }, []);

  const createAccount = async (username) => {
    const user = await api.createAccount(username);
    setUser(user);
    return user;
  };

  const addChat = (chat) => {
    setChats((prev) => [...prev, chat]);
  };

  const refreshChats = async () => {
    const chats = await api.getChats();
    setChats(chats);
  };

  return (
    <UserContext.Provider
      value={{
        user,
        chats,
        teams,
        team,
        createAccount,
        addChat,
        refreshChats,
      }}
    >
      {children}
    </UserContext.Provider>
  );
}

export const useUser = () => useContext(UserContext);
