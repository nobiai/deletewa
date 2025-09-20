import React, { useState, useEffect } from "react";
import "./App.css";
import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Helper functions
const formatTime = (timestamp) => {
  const date = new Date(timestamp);
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
};

const formatDate = (timestamp) => {
  const date = new Date(timestamp);
  const today = new Date();
  const yesterday = new Date(today);
  yesterday.setDate(yesterday.getDate() - 1);
  
  if (date.toDateString() === today.toDateString()) {
    return 'Today';
  } else if (date.toDateString() === yesterday.toDateString()) {
    return 'Yesterday';
  } else {
    return date.toLocaleDateString();
  }
};

// Components
const StatsCard = ({ title, value, icon, color }) => (
  <div className="bg-white rounded-xl shadow-md p-6 border-l-4" style={{ borderLeftColor: color }}>
    <div className="flex items-center justify-between">
      <div>
        <p className="text-gray-600 text-sm font-medium">{title}</p>
        <p className="text-3xl font-bold text-gray-900">{value}</p>
      </div>
      <div className="text-4xl" style={{ color }}>{icon}</div>
    </div>
  </div>
);

const ChatItem = ({ chat, onSelect, isSelected }) => (
  <div 
    className={`flex items-center p-4 hover:bg-gray-50 cursor-pointer transition-colors ${
      isSelected ? 'bg-blue-50 border-r-2 border-blue-500' : ''
    }`}
    onClick={() => onSelect(chat)}
  >
    <img 
      src={chat.profile_picture || 'https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?w=40&h=40&fit=crop&crop=face'} 
      alt={chat.name}
      className="w-12 h-12 rounded-full object-cover"
    />
    <div className="ml-3 flex-1">
      <div className="flex items-center justify-between">
        <h3 className="font-semibold text-gray-900">{chat.name}</h3>
        <span className="text-xs text-gray-500">
          {chat.chat_type === 'group' ? '👥' : '👤'}
        </span>
      </div>
      <p className="text-sm text-gray-600">
        {chat.deleted_messages_count} deleted message{chat.deleted_messages_count !== 1 ? 's' : ''}
      </p>
    </div>
    {chat.deleted_messages_count > 0 && (
      <div className="bg-red-500 text-white text-xs px-2 py-1 rounded-full">
        {chat.deleted_messages_count}
      </div>
    )}
  </div>
);

const MessageItem = ({ message, chat }) => (
  <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-3">
    <div className="flex items-start justify-between">
      <div className="flex items-center space-x-3">
        <img 
          src={chat?.profile_picture || 'https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?w=32&h=32&fit=crop&crop=face'} 
          alt={message.sender_name}
          className="w-8 h-8 rounded-full object-cover"
        />
        <div>
          <p className="font-medium text-gray-900">{message.sender_name}</p>
          <p className="text-sm text-gray-600">{chat?.name}</p>
        </div>
      </div>
      <div className="text-right">
        <p className="text-xs text-gray-500">{formatDate(message.timestamp)}</p>
        <p className="text-xs text-gray-500">{formatTime(message.timestamp)}</p>
        <span className="text-xs bg-red-100 text-red-600 px-2 py-1 rounded-full">
          Deleted {formatTime(message.deleted_at)}
        </span>
      </div>
    </div>
    <div className="mt-3 p-3 bg-white rounded-lg border-l-4 border-red-400">
      <p className="text-gray-800">{message.content}</p>
      {message.message_type !== 'text' && (
        <span className="text-xs text-gray-500 italic">
          [{message.message_type.toUpperCase()}]
        </span>
      )}
    </div>
  </div>
);

const EmptyState = ({ title, description, icon }) => (
  <div className="text-center py-12">
    <div className="text-6xl mb-4">{icon}</div>
    <h3 className="text-xl font-semibold text-gray-900 mb-2">{title}</h3>
    <p className="text-gray-600">{description}</p>
  </div>
);

function App() {
  const [deletedMessages, setDeletedMessages] = useState([]);
  const [chats, setChats] = useState([]);
  const [selectedChat, setSelectedChat] = useState(null);
  const [stats, setStats] = useState({});
  const [loading, setLoading] = useState(true);
  const [autoRefresh, setAutoRefresh] = useState(true);

  // Initialize sample data
  const initializeSampleData = async () => {
    try {
      await axios.post(`${API}/init-sample-data`);
    } catch (error) {
      console.error('Error initializing sample data:', error);
    }
  };

  // Fetch data functions
  const fetchDeletedMessages = async (chatId = null) => {
    try {
      const url = chatId ? `${API}/messages?chat_id=${chatId}&status=deleted` : `${API}/messages/deleted`;
      const response = await axios.get(url);
      setDeletedMessages(response.data);
    } catch (error) {
      console.error('Error fetching deleted messages:', error);
    }
  };

  const fetchChats = async () => {
    try {
      const response = await axios.get(`${API}/chats`);
      setChats(response.data);
    } catch (error) {
      console.error('Error fetching chats:', error);
    }
  };

  const fetchStats = async () => {
    try {
      const response = await axios.get(`${API}/stats`);
      setStats(response.data);
    } catch (error) {
      console.error('Error fetching stats:', error);
    }
  };

  const loadAllData = async () => {
    setLoading(true);
    await Promise.all([
      fetchDeletedMessages(selectedChat?.id),
      fetchChats(),
      fetchStats()
    ]);
    setLoading(false);
  };

  // Handle chat selection
  const handleChatSelect = (chat) => {
    setSelectedChat(chat);
    fetchDeletedMessages(chat.id);
  };

  const handleShowAll = () => {
    setSelectedChat(null);
    fetchDeletedMessages();
  };

  // Auto-refresh functionality
  useEffect(() => {
    let interval;
    if (autoRefresh) {
      interval = setInterval(() => {
        loadAllData();
      }, 10000); // Refresh every 10 seconds
    }
    return () => clearInterval(interval);
  }, [autoRefresh, selectedChat]);

  // Initial load
  useEffect(() => {
    const initialize = async () => {
      await initializeSampleData();
      await loadAllData();
    };
    initialize();
  }, []);

  const chatWithMessages = selectedChat ? chats.find(c => c.id === selectedChat.id) : null;

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading WhatsApp deleted messages...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="text-3xl">🔍</div>
              <div>
                <h1 className="text-2xl font-bold text-gray-900">WhatsApp Message Recovery</h1>
                <p className="text-gray-600">Track and recover deleted messages</p>
              </div>
            </div>
            <div className="flex items-center space-x-4">
              <button
                onClick={() => setAutoRefresh(!autoRefresh)}
                className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                  autoRefresh 
                    ? 'bg-green-100 text-green-800 hover:bg-green-200' 
                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                }`}
              >
                {autoRefresh ? '🔄 Auto Refresh ON' : '⏸️ Auto Refresh OFF'}
              </button>
              <button
                onClick={loadAllData}
                className="bg-blue-500 hover:bg-blue-600 text-white px-4 py-2 rounded-lg font-medium transition-colors"
              >
                🔄 Refresh Now
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Stats Section */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
          <StatsCard 
            title="Total Deleted" 
            value={stats.total_deleted || 0} 
            icon="🗑️" 
            color="#ef4444" 
          />
          <StatsCard 
            title="Today" 
            value={stats.today_deleted || 0} 
            icon="📅" 
            color="#f59e0b" 
          />
          <StatsCard 
            title="This Week" 
            value={stats.this_week_deleted || 0} 
            icon="📊" 
            color="#10b981" 
          />
          <StatsCard 
            title="Most Active Chat" 
            value={stats.most_active_chat || "None"} 
            icon="💬" 
            color="#6366f1" 
          />
        </div>

        {/* Main Content */}
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          {/* Chat List */}
          <div className="lg:col-span-1">
            <div className="bg-white rounded-xl shadow-md overflow-hidden">
              <div className="bg-gray-50 px-4 py-3 border-b">
                <div className="flex items-center justify-between">
                  <h2 className="font-semibold text-gray-900">Chats</h2>
                  <button
                    onClick={handleShowAll}
                    className={`text-sm px-3 py-1 rounded-full transition-colors ${
                      !selectedChat 
                        ? 'bg-blue-500 text-white' 
                        : 'bg-gray-200 text-gray-600 hover:bg-gray-300'
                    }`}
                  >
                    All
                  </button>
                </div>
              </div>
              <div className="max-h-96 overflow-y-auto">
                {chats.length === 0 ? (
                  <div className="p-4 text-center text-gray-500">
                    <p>No chats found</p>
                  </div>
                ) : (
                  chats.map(chat => (
                    <ChatItem
                      key={chat.id}
                      chat={chat}
                      onSelect={handleChatSelect}
                      isSelected={selectedChat?.id === chat.id}
                    />
                  ))
                )}
              </div>
            </div>
          </div>

          {/* Messages List */}
          <div className="lg:col-span-3">
            <div className="bg-white rounded-xl shadow-md overflow-hidden">
              <div className="bg-gray-50 px-6 py-4 border-b">
                <h2 className="font-semibold text-gray-900">
                  {selectedChat ? `Deleted Messages from ${selectedChat.name}` : 'All Deleted Messages'}
                </h2>
                <p className="text-sm text-gray-600 mt-1">
                  {deletedMessages.length} deleted message{deletedMessages.length !== 1 ? 's' : ''} found
                </p>
              </div>
              <div className="p-6 max-h-96 overflow-y-auto">
                {deletedMessages.length === 0 ? (
                  <EmptyState
                    title="No deleted messages"
                    description={selectedChat ? 
                      `No deleted messages found in ${selectedChat.name}` : 
                      "No deleted messages found in any chat"
                    }
                    icon="✨"
                  />
                ) : (
                  deletedMessages.map(message => (
                    <MessageItem
                      key={message.id}
                      message={message}
                      chat={chatWithMessages || chats.find(c => c.id === message.chat_id)}
                    />
                  ))
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;