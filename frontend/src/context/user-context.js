'use client';

import { createContext, useContext, useEffect, useState } from 'react';
import { api } from '@/lib/api';
import { webSocketService } from '../lib/project-websocket';

const UserContext = createContext({
  user: null,
  team: null,
  teams: [],
  chats: [],
  projects: [],
  createAccount: async () => {},
  addChat: async () => {},
  refreshChats: async () => {},
  refreshProjects: async () => {},
});

export function UserProvider({ children }) {
  const [user, setUser] = useState(null);
  const [chats, setChats] = useState([]);
  const [teams, setTeams] = useState([]);
  const [team, setTeam] = useState(null);
  const [projects, setProjects] = useState([]);

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

  useEffect(() => {
    if (team?.id) {
      api.getTeamProjects(team.id).then(setProjects);
    }
  }, [team?.id]);

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

  const refreshProjects = async () => {
    const projects = await api.getTeamProjects(team.id);
    setProjects(projects);
  };

  return (
    <UserContext.Provider
      value={{
        user,
        chats,
        teams,
        team,
        projects,
        createAccount,
        addChat,
        refreshChats,
        refreshProjects,
      }}
    >
      {children}
    </UserContext.Provider>
  );
}

export const useUser = () => useContext(UserContext);
