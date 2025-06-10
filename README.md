# Task Management System

A collaborative task management system built with FastAPI, Firebase Authentication, and Firestore.

*Student Name:* Naveen Alakunta


## Features

- User authentication via Firebase Auth
- Create, view, edit, and delete task boards
- Add members to boards for collaboration
- Create, assign, edit, and delete tasks
- Mark tasks as complete
- Track task statistics (active, completed, total)
- Role-based permissions (board creator vs. members)

## Setup Instructions

### Prerequisites

- Python 3.8+
- Firebase account with Authentication and Firestore enabled

### Installation

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/task-management-system.git
   cd task-management-system
   ```

2. Create a virtual environment and install dependencies:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. Set up Firebase:
   - Create a Firebase project in the [Firebase Console](https://console.firebase.google.com/)
   - Enable Email/Password and Google authentication methods
   - Create a Firestore database in production mode

4. Create a `.env` file with your Firebase configuration:
   ```
   FIREBASE_API_KEY=your-api-key
   FIREBASE_AUTH_DOMAIN=your-project-id.firebaseapp.com
   FIREBASE_PROJECT_ID=your-project-id
   FIREBASE_STORAGE_BUCKET=your-project-id.appspot.com
   FIREBASE_MESSAGING_SENDER_ID=your-messaging-sender-id
   FIREBASE_APP_ID=your-app-id
   ```

5. Run the application:
   ```
   uvicorn main:app
   ```

6. Open your browser and navigate to `http://localhost:8000`

## Code Documentation

### Backend (main.py)

#### Authentication

- `get_current_user(request)`: Middleware that verifies the Firebase ID token from cookies and returns the user information.
- `set_auth_cookie(request, response, data)`: Sets the authentication cookie with the Firebase ID token.
- `logout(response)`: Clears the authentication cookie.

#### Board Management

- `get_boards(user)`: Retrieves all boards where the user is either the creator or a member.
- `create_board(data, user)`: Creates a new board with the current user as the creator.
- `get_board(board_id, user)`: Retrieves a specific board and its tasks if the user has access.
- `update_board(board_id, data, user)`: Updates a board's title if the user is the creator.
- `delete_board(board_id, user)`: Deletes a board if the user is the creator and there are no members or tasks.

#### Member Management

- `add_member(board_id, data, user)`: Adds a member to a board if the user is the creator.
- `remove_member(board_id, member_id, user)`: Removes a member from a board if the user is the creator.

#### Task Management

- `create_task(board_id, data, user)`: Creates a new task in a board if the user has access.
- `update_task(board_id, task_id, data, user)`: Updates a task if the user has access.
- `delete_task(board_id, task_id, user)`: Deletes a task if the user has access.
- `get_task_stats(board_id, user)`: Retrieves task statistics (active, completed, total) for a board.

### Frontend

#### Authentication (firebase-auth.js)

- `login()`: Handles user login with email and password.
- `handleGoogleSignin()`: Handles Google sign-in.
- `sendTokenToServer(user)`: Sends the Firebase ID token to the server to set the auth cookie.
- `logout()`: Signs out the user from Firebase and clears the server-side cookie.

#### Board Management (boards.html)

- `fetchBoards()`: Retrieves and displays all boards the user has access to.
- `createBoard()`: Creates a new board.
- `openBoard(boardId)`: Navigates to a specific board.

#### Task Management (board.html)

- `fetchBoardData()`: Retrieves and displays board details and tasks.
- `fetchTaskStats()`: Retrieves and displays task statistics.
- `addTask()`: Creates a new task.
- `updateTask()`: Updates an existing task.
- `deleteTask(taskId)`: Deletes a task.
- `toggleTaskCompletion(taskId, completed)`: Marks a task as completed or active.
- `updateBoardTitle()`: Updates the board title.
- `deleteBoard()`: Deletes the board.
- `addMember()`: Adds a member to the board.
- `removeMember()`: Removes a member from the board.

## Implementation Details

This application uses:
- FastAPI for the backend framework
- Firebase Authentication for user authentication
- Firestore for database storage
- Direct REST API calls to Firebase services

The backend communicates with Firebase services through their REST APIs:
- Firebase Authentication REST API for user authentication and management
- Firestore REST API for database operations

## Security Considerations

- Authentication is handled by Firebase Auth, a secure authentication service.
- Server-side validation ensures users can only access boards they have permission for.
- Only the board creator can add/remove members or delete the board.
- All API endpoints verify user authentication and authorization.

## Data Model

### Board
- `title`: String - The name of the board
- `creator_id`: String - The ID of the user who created the board
- `creator_email`: String - The email of the user who created the board
- `members`: Array - List of user IDs who have access to the board
- `created_at`: Timestamp - When the board was created

### Task
- `title`: String - The name of the task
- `due_date`: String - When the task is due
- `assigned_to`: String - The ID of the user assigned to the task
- `completed`: Boolean - Whether the task is completed
- `created_by`: String - The ID of the user who created the task
- `created_at`: Timestamp - When the task was created
- `completed_at`: Timestamp - When the task was marked as completed
- `unassigned`: Boolean - Whether the task was unassigned due to member removal
