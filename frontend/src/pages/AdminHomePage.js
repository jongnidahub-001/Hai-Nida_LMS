import React, { useEffect, useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { useNavigate } from 'react-router-dom';
import Header from '../components/Header';
import './AdminHomePage.css';

function AdminHomePage() {
  const { user, getAuthHeader } = useAuth();
  const navigate = useNavigate();
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [showAddUserModal, setShowAddUserModal] = useState(false);
  const [newUserEmail, setNewUserEmail] = useState('');
  const [addingUser, setAddingUser] = useState(false);
  const [addUserError, setAddUserError] = useState('');

  useEffect(() => {
    // Redirect if not admin
    if (!user || user.role !== 'admin') {
      navigate('/login');
      return;
    }

    fetchUsers();
  }, [user, navigate]);

  const fetchUsers = async () => {
    try {
      const response = await fetch('http://localhost:5000/api/admin/users', {
        headers: {
          ...getAuthHeader(),
          'Content-Type': 'application/json'
        }
      });
      
      if (response.ok) {
        const data = await response.json();
        setUsers(data.users || []);
      } else {
        console.error('Failed to fetch users');
      }
    } catch (error) {
      console.error('Error fetching users:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleAddUser = async (e) => {
    e.preventDefault();
    setAddUserError('');
    setAddingUser(true);

    try {
      const response = await fetch('http://localhost:5000/api/admin/add-user', {
        method: 'POST',
        headers: {
          ...getAuthHeader(),
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          email: newUserEmail
        })
      });

      const data = await response.json();

      if (data.success) {
        setShowAddUserModal(false);
        setNewUserEmail('');
        fetchUsers(); // Refresh the user list
        alert('User added successfully! Default password: haionetime1234');
      } else {
        setAddUserError(data.message || 'Failed to add user');
      }
    } catch (error) {
      setAddUserError('Error adding user');
    } finally {
      setAddingUser(false);
    }
  };

  const filteredUsers = users.filter(user => 
    user.username.toLowerCase().includes(searchTerm.toLowerCase()) ||
    user.email.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="admin-home-bg">
      <Header />
      
      <div className="container mt-4">
        <div className="box admin-home-card">
          <div className="is-flex is-justify-content-space-between is-align-items-center mb-4">
            <div className="is-size-4 has-text-weight-bold">All Users</div>
            <div className="is-flex is-align-items-center">
              <button 
                className="button is-primary mr-3"
                onClick={() => setShowAddUserModal(true)}
              >
                <span className="icon">
                  <i className="fas fa-plus"></i>
                </span>
                <span>Add User</span>
              </button>
              <div className="field">
                <div className="control has-icons-left">
                  <input
                    className="input is-small"
                    type="text"
                    placeholder="Search users..."
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                  />
                  <span className="icon is-small is-left">
                    <i className="fas fa-search"></i>
                  </span>
                </div>
              </div>
            </div>
          </div>

          {loading ? (
            <div className="has-text-centered">
              <div className="is-size-6">Loading users...</div>
            </div>
          ) : filteredUsers.length === 0 ? (
            <div className="has-text-centered">
              <div className="is-size-6 has-text-grey">No users found</div>
            </div>
          ) : (
            <div className="table-container">
              <table className="table is-fullwidth is-hoverable">
                <thead>
                  <tr>
                    <th>Username</th>
                    <th>Email</th>
                    <th>Role</th>
                    <th>Status</th>
                    <th>Auth Status</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredUsers.map((user) => (
                    <tr key={user.user_id}>
                      <td>{user.username}</td>
                      <td>{user.email}</td>
                      <td>
                        <span className={`tag ${user.role === 'admin' ? 'is-danger' : 'is-info'}`}>
                          {user.role}
                        </span>
                      </td>
                      <td>
                        <span className="tag is-success">Active</span>
                      </td>
                      <td>
                        <span className={`tag ${user.is_auth ? 'is-success' : 'is-warning'}`}>
                          {user.is_auth ? 'Authenticated' : 'First Login Required'}
                        </span>
                      </td>
                      <td>
                        <button 
                          className="button is-small is-info"
                          onClick={() => navigate(`/admin/user/${user.user_id}`)}
                        >
                          View Details
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>

      {/* Add User Modal */}
      <div className={`modal ${showAddUserModal ? 'is-active' : ''}`}>
        <div className="modal-background" onClick={() => setShowAddUserModal(false)}></div>
        <div className="modal-card" style={{ backgroundColor: 'white' }}>
          <header className="modal-card-head" style={{ backgroundColor: 'white', borderBottom: '1px solid var(--medium-grey)' }}>
            <p className="modal-card-title" style={{ color: 'var(--primary-black)', fontWeight: 'bold' }}>Add New User</p>
            <button 
              className="delete" 
              onClick={() => setShowAddUserModal(false)}
              disabled={addingUser}
            ></button>
          </header>
          <section className="modal-card-body" style={{ backgroundColor: 'white' }}>
            <form onSubmit={handleAddUser}>
              <div className="field">
                <label className="label" style={{ color: 'var(--primary-black)', fontWeight: '600' }}>Email Address</label>
                <div className="control">
                  <input
                    className="input"
                    type="email"
                    placeholder="Enter user email"
                    value={newUserEmail}
                    onChange={(e) => setNewUserEmail(e.target.value)}
                    required
                    disabled={addingUser}
                    style={{ 
                      borderColor: 'var(--medium-grey)',
                      color: 'var(--primary-black)'
                    }}
                  />
                </div>
                <p className="help" style={{ color: 'var(--primary-black)', fontSize: '0.875rem' }}>
                  User will receive default password: <strong style={{ color: 'var(--primary-black)' }}>haionetime1234</strong>
                </p>
              </div>
              {addUserError && (
                <div className="notification is-danger is-light" style={{ backgroundColor: '#fef7f7', borderColor: '#f14668', color: '#cc0f35' }}>
                  {addUserError}
                </div>
              )}
            </form>
          </section>
          <footer className="modal-card-foot" style={{ backgroundColor: 'white', borderTop: '1px solid var(--medium-grey)', gap: '12px' }}>
            <button 
              className={`button is-primary ${addingUser ? 'is-loading' : ''}`}
              onClick={handleAddUser}
              disabled={addingUser || !newUserEmail}
              style={{ 
                backgroundColor: 'var(--primary-color)',
                borderColor: 'var(--primary-color)',
                color: 'white'
              }}
            >
              Add User
            </button>
            <button 
              className="button" 
              onClick={() => setShowAddUserModal(false)}
              disabled={addingUser}
              style={{ 
                backgroundColor: 'white',
                borderColor: 'var(--medium-grey)',
                color: 'var(--primary-black)'
              }}
            >
              Cancel
            </button>
          </footer>
        </div>
      </div>
    </div>
  );
}

export default AdminHomePage; 