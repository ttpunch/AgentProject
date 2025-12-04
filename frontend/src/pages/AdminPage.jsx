import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import './AdminPage.css';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export default function AdminPage() {
    const { user, token, isAdmin, loading: authLoading } = useAuth();
    const [users, setUsers] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const [success, setSuccess] = useState('');
    const [selectedUser, setSelectedUser] = useState(null);
    const [newPassword, setNewPassword] = useState('');
    const navigate = useNavigate();

    useEffect(() => {
        if (!authLoading && !isAdmin) {
            navigate('/chat');
        }
    }, [isAdmin, authLoading, navigate]);

    useEffect(() => {
        if (token && isAdmin) {
            fetchUsers();
        }
    }, [token, isAdmin]);

    const fetchUsers = async () => {
        try {
            const res = await axios.get(`${API_URL}/admin/users`, {
                headers: { Authorization: `Bearer ${token}` }
            });
            setUsers(res.data);
        } catch (err) {
            setError('Failed to fetch users');
        } finally {
            setLoading(false);
        }
    };

    const handleResetPassword = async (userId) => {
        if (!newPassword || newPassword.length < 6) {
            setError('Password must be at least 6 characters');
            return;
        }

        try {
            await axios.put(`${API_URL}/admin/users/${userId}/password`,
                { new_password: newPassword },
                { headers: { Authorization: `Bearer ${token}` } }
            );
            setSuccess('Password updated successfully');
            setSelectedUser(null);
            setNewPassword('');
            setTimeout(() => setSuccess(''), 3000);
        } catch (err) {
            setError(err.response?.data?.detail || 'Failed to reset password');
        }
    };

    if (authLoading || loading) {
        return <div className="admin-loading">Loading...</div>;
    }

    if (!isAdmin) {
        return null;
    }

    return (
        <div className="admin-container">
            <div className="admin-header">
                <h1>👥 User Management</h1>
                <p>Manage users and reset passwords</p>
            </div>

            {error && <div className="admin-error">{error}</div>}
            {success && <div className="admin-success">{success}</div>}

            <div className="users-table-container">
                <table className="users-table">
                    <thead>
                        <tr>
                            <th>Username</th>
                            <th>Email</th>
                            <th>Role</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        {users.map((u) => (
                            <tr key={u.id}>
                                <td>{u.username}</td>
                                <td>{u.email}</td>
                                <td>
                                    <span className={`role-badge ${u.role}`}>
                                        {u.role}
                                    </span>
                                </td>
                                <td>
                                    {selectedUser === u.id ? (
                                        <div className="reset-form">
                                            <input
                                                type="password"
                                                placeholder="New password"
                                                value={newPassword}
                                                onChange={(e) => setNewPassword(e.target.value)}
                                            />
                                            <button
                                                className="btn-confirm"
                                                onClick={() => handleResetPassword(u.id)}
                                            >
                                                ✓
                                            </button>
                                            <button
                                                className="btn-cancel"
                                                onClick={() => {
                                                    setSelectedUser(null);
                                                    setNewPassword('');
                                                }}
                                            >
                                                ✕
                                            </button>
                                        </div>
                                    ) : (
                                        <button
                                            className="btn-reset"
                                            onClick={() => setSelectedUser(u.id)}
                                        >
                                            Reset Password
                                        </button>
                                    )}
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
}
