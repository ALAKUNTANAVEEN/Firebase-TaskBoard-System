# main.py

from fastapi import FastAPI, Request, Response, Depends, HTTPException, Body
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from dotenv import load_dotenv
import os
import json
import requests
from datetime import datetime
from typing import List, Optional

# Load environment variables
load_dotenv()

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Firebase configuration
FIREBASE_API_KEY = os.getenv("FIREBASE_API_KEY")
FIREBASE_PROJECT_ID = os.getenv("FIREBASE_PROJECT_ID")
FIREBASE_AUTH_DOMAIN = os.getenv("FIREBASE_AUTH_DOMAIN")

# Firebase Auth REST API endpoints
FIREBASE_AUTH_SIGNIN_URL = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={FIREBASE_API_KEY}"
FIREBASE_AUTH_SIGNUP_URL = f"https://identitytoolkit.googleapis.com/v1/accounts:signUp?key={FIREBASE_API_KEY}"
FIREBASE_AUTH_USER_INFO_URL = f"https://identitytoolkit.googleapis.com/v1/accounts:lookup?key={FIREBASE_API_KEY}"
FIREBASE_AUTH_RESET_PASSWORD_URL = f"https://identitytoolkit.googleapis.com/v1/accounts:sendOobCode?key={FIREBASE_API_KEY}"
FIREBASE_AUTH_VERIFY_PASSWORD_RESET_URL = f"https://identitytoolkit.googleapis.com/v1/accounts:resetPassword?key={FIREBASE_API_KEY}"
FIREBASE_AUTH_UPDATE_PROFILE_URL = f"https://identitytoolkit.googleapis.com/v1/accounts:update?key={FIREBASE_API_KEY}"

# Firestore REST API base URL
FIRESTORE_BASE_URL = f"https://firestore.googleapis.com/v1/projects/{FIREBASE_PROJECT_ID}/databases/(default)/documents"
FIRESTORE_QUERY_URL = f"https://firestore.googleapis.com/v1/projects/{FIREBASE_PROJECT_ID}/databases/(default)/documents:runQuery"

# Helper function to convert Firestore document to Python dict
def firestore_doc_to_dict(doc, include_id=True):
    if not doc or "fields" not in doc:
        return None
    
    result = {}
    for field, value in doc["fields"].items():
        # Extract the actual value based on type
        for type_key, actual_value in value.items():
            if type_key == "stringValue":
                result[field] = actual_value
            elif type_key == "integerValue":
                result[field] = int(actual_value)
            elif type_key == "doubleValue":
                result[field] = float(actual_value)
            elif type_key == "booleanValue":
                result[field] = actual_value
            elif type_key == "timestampValue":
                result[field] = actual_value
            elif type_key == "arrayValue":
                if "values" in actual_value:
                    result[field] = [
                        list(v.values())[0] for v in actual_value["values"]
                        if len(v) > 0
                    ]
                else:
                    result[field] = []
            elif type_key == "mapValue":
                if "fields" in actual_value:
                    nested_doc = {"fields": actual_value["fields"]}
                    result[field] = firestore_doc_to_dict(nested_doc, include_id=False)
                else:
                    result[field] = {}
    
    # Add document ID if requested and available
    if include_id and "name" in doc:
        result["id"] = doc["name"].split("/")[-1]
    
    return result

# Helper function to convert Python value to Firestore value
def to_firestore_value(value):
    if value is None:
        return {"nullValue": None}
    elif isinstance(value, str):
        return {"stringValue": value}
    elif isinstance(value, bool):
        return {"booleanValue": value}
    elif isinstance(value, int):
        return {"integerValue": str(value)}
    elif isinstance(value, float):
        return {"doubleValue": value}
    elif isinstance(value, list):
        return {
            "arrayValue": {
                "values": [to_firestore_value(item) for item in value]
            }
        }
    elif isinstance(value, dict):
        return {
            "mapValue": {
                "fields": {k: to_firestore_value(v) for k, v in value.items()}
            }
        }
    else:
        return {"stringValue": str(value)}

# Helper function to convert Python dict to Firestore fields
def dict_to_firestore_fields(data):
    return {k: to_firestore_value(v) for k, v in data.items()}

# Authentication middleware
async def get_current_user(request: Request):
    token = request.cookies.get("auth_token")
    if not token:
        return None
    
    try:
        # Verify token with Firebase Auth REST API
        response = requests.post(
            FIREBASE_AUTH_USER_INFO_URL,
            json={"idToken": token}
        )
        
        if response.status_code != 200:
            return None
            
        user_data = response.json()
        if "users" not in user_data or not user_data["users"]:
            return None
            
        user_info = user_data["users"][0]
        
        return {
            "id": user_info.get("localId"),
            "email": user_info.get("email", "")
        }
    except Exception as e:
        print(f"Auth error: {e}")
        return None

# Helper function to get user by email
async def get_user_by_email(email):
    try:
        # Query Firestore for user by email
        query = {
            "structuredQuery": {
                "from": [{"collectionId": "users"}],
                "where": {
                    "fieldFilter": {
                        "field": {"fieldPath": "email"},
                        "op": "EQUAL",
                        "value": {"stringValue": email}
                    }
                },
                "limit": 1
            }
        }
        
        response = requests.post(FIRESTORE_QUERY_URL, json=query)
        
        if response.status_code != 200:
            return None
            
        results = response.json()
        for result in results:
            if "document" in result:
                user_data = firestore_doc_to_dict(result["document"])
                return user_data
        
        # If not found in Firestore, try Firebase Auth
        # This requires an admin token which we don't have, so we'll use a workaround
        # We'll create a temporary user record in Firestore
        
        # First, check if the user exists in Firebase Auth
        # We can't do this directly without admin SDK, so we'll rely on the frontend
        # to handle this part
        
        return None
    except Exception as e:
        print(f"Error getting user by email: {e}")
        return None

# Helper function to get user by ID
async def get_user_by_id(user_id):
    try:
        # Try to get user from Firestore first
        response = requests.get(f"{FIRESTORE_BASE_URL}/users/{user_id}")
        
        if response.status_code == 200:
            user_data = firestore_doc_to_dict(response.json())
            return user_data
        
        # If not found in Firestore, we can't get from Firebase Auth without admin SDK
        # We'll return minimal info based on what we know
        return {
            "id": user_id,
            "email": "",
            "display_name": ""
        }
    except Exception as e:
        print(f"Error getting user by ID: {e}")
        return {
            "id": user_id,
            "email": "",
            "display_name": ""
        }

# Route for setting auth cookie
@app.post("/api/set-auth-cookie")
async def set_auth_cookie(request: Request, response: Response, data: dict = Body(...)):
    token = data.get("token")
    if token:
        # Set cookie with token
        response.set_cookie(key="auth_token", value=token, httponly=True, secure=True, samesite="strict")
        return {"success": True}
    return {"success": False}

# Route for clearing auth cookie (logout)
@app.post("/api/logout")
async def logout(response: Response):
    response.delete_cookie(key="auth_token")
    return {"success": True}

# Home/Login page
@app.get("/", response_class=HTMLResponse)
async def home(request: Request, user: dict = Depends(get_current_user)):
    if user:
        return RedirectResponse(url="/boards")
    return templates.TemplateResponse("login.html", {"request": request})

# Sign Up page
@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

# Forget password page
@app.get("/forgot-password", response_class=HTMLResponse)
async def forgot_password_page(request: Request):
    return templates.TemplateResponse("forget-password.html", {"request": request})

# Reset password page
@app.get("/reset-password", response_class=HTMLResponse)
async def reset_password_page(request: Request, mode: str = None, oobCode: str = None):
    """Handle password reset redirects from Firebase"""
    return templates.TemplateResponse("reset-password.html", {
        "request": request,
        "mode": mode,
        "oob_code": oobCode
    })

# Boards page
@app.get("/boards", response_class=HTMLResponse)
async def boards_page(request: Request, user: dict = Depends(get_current_user)):
    if not user:
        return RedirectResponse(url="/")
    return templates.TemplateResponse("boards.html", {"request": request, "user": user})

# Single board page
@app.get("/board/{board_id}", response_class=HTMLResponse)
async def board_page(request: Request, board_id: str, user: dict = Depends(get_current_user)):
    if not user:
        return RedirectResponse(url="/")
    
    # Check if user has access to this board
    try:
        response = requests.get(f"{FIRESTORE_BASE_URL}/boards/{board_id}")
        
        if response.status_code != 200:
            return RedirectResponse(url="/boards")
            
        board_data = firestore_doc_to_dict(response.json())
        
        if user["id"] != board_data.get("creator_id") and user["id"] not in board_data.get("members", []):
            return RedirectResponse(url="/boards")
        
        return templates.TemplateResponse("board.html", {
            "request": request, 
            "user": user,
            "board_id": board_id
        })
    except Exception as e:
        print(f"Error accessing board: {e}")
        return RedirectResponse(url="/boards")

# Profile page
@app.get("/profile", response_class=HTMLResponse)
async def profile_page(request: Request, user: dict = Depends(get_current_user)):
    if not user:
        return RedirectResponse(url="/")
    
    try:
        # Get user info from Firebase Auth
        response = requests.post(
            FIREBASE_AUTH_USER_INFO_URL,
            json={"idToken": request.cookies.get("auth_token")}
        )
        
        if response.status_code != 200:
            return RedirectResponse(url="/boards")
            
        user_data = response.json()
        user_info = user_data.get("users", [])[0]
        
        # Format user data for the template
        user_data = {
            "uid": user_info.get("localId"),
            "email": user_info.get("email"),
            "display_name": user_info.get("displayName"),
            "email_verified": user_info.get("emailVerified"),
            "created_at": user_info.get("createdAt"),
            "last_login": user_info.get("lastLoginAt")
        }
        
        return templates.TemplateResponse("profile.html", {"request": request, "user": user_data})
    except Exception as e:
        print(f"Error getting user profile: {e}")
        return RedirectResponse(url="/boards")

# API endpoint for update user profile
@app.post("/api/update-profile")
async def update_profile(request: Request, data: dict = Body(...)):
    user_token = request.cookies.get("auth_token")
    if not user_token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        # Update user profile in Firebase Auth
        display_name = data.get("display_name")
        
        # Update the user record using Firebase Auth REST API
        response = requests.post(
            FIREBASE_AUTH_UPDATE_PROFILE_URL,
            json={
                "idToken": user_token,
                "displayName": display_name,
                "returnSecureToken": True
            }
        )
        
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail=response.text)
        
        return {"success": True, "message": "Profile updated successfully"}
    except Exception as e:
        print(f"Error updating profile: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# API endpoints for boards
@app.get("/api/boards")
async def get_boards(user: dict = Depends(get_current_user)):
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Get boards where user is creator
    creator_query = {
        "structuredQuery": {
            "from": [{"collectionId": "boards"}],
            "where": {
                "fieldFilter": {
                    "field": {"fieldPath": "creator_id"},
                    "op": "EQUAL",
                    "value": {"stringValue": user["id"]}
                }
            }
        }
    }
    
    creator_boards_response = requests.post(
        FIRESTORE_QUERY_URL,
        json=creator_query
    )
    
    # Get boards where user is member
    member_query = {
        "structuredQuery": {
            "from": [{"collectionId": "boards"}],
            "where": {
                "fieldFilter": {
                    "field": {"fieldPath": "members"},
                    "op": "ARRAY_CONTAINS",
                    "value": {"stringValue": user["id"]}
                }
            }
        }
    }
    
    member_boards_response = requests.post(
        FIRESTORE_QUERY_URL,
        json=member_query
    )
    
    boards = []
    
    # Process creator boards
    for doc in creator_boards_response.json():
        if "document" in doc:
            board_data = firestore_doc_to_dict(doc["document"])
            if board_data:
                print(f"Board: {board_data}")
                board_data["is_creator"] = True
                boards.append(board_data)
    
    # Process member boards
    for doc in member_boards_response.json():
        if "document" in doc:
            board_data = firestore_doc_to_dict(doc["document"])
            if board_data:
                print(f"Board: {board_data}")
                board_data["is_creator"] = False
                boards.append(board_data)
    
    # print(f"Boards: {boards}")
    return {"boards": boards}

@app.post("/api/boards")
async def create_board(data: dict = Body(...), user: dict = Depends(get_current_user)):
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    title = data.get("title")
    if not title:
        raise HTTPException(status_code=400, detail="Board title is required")
    
    # Create new board in Firestore
    new_board = {
        "fields": dict_to_firestore_fields({
            "title": title,
            "creator_id": user["id"],
            "creator_email": user["email"],
            "members": [],
            "created_at": datetime.now().isoformat()
        })
    }
    
    response = requests.post(
        f"{FIRESTORE_BASE_URL}/boards",
        json=new_board
    )
    
    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail=response.text)
    
    board_data = response.json()
    board_id = board_data["name"].split("/")[-1]
    
    return {
        "id": board_id,
        "title": title,
        "creator_id": user["id"],
        "creator_email": user["email"],
        "members": [],
        "created_at": datetime.now().isoformat()
    }

@app.get("/api/boards/{board_id}")
async def get_board(board_id: str, request: Request, user: dict = Depends(get_current_user)):
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Get board data
    response = requests.get(f"{FIRESTORE_BASE_URL}/boards/{board_id}")
    
    if response.status_code != 200:
        raise HTTPException(status_code=404, detail="Board not found")
    
    board_data = firestore_doc_to_dict(response.json())
    
    # Check if user has access
    if user["id"] != board_data.get("creator_id") and user["id"] not in board_data.get("members", []):
        raise HTTPException(status_code=403, detail="Access denied")
    
    board_data["is_creator"] = user["id"] == board_data.get("creator_id")

    # Get member details
    members_data = []
    auth_token = request.cookies.get("auth_token")
    
    for member_id in board_data.get("members", []):
        try:
            # For members, we'll use a simplified approach since we can't directly
            # query Firebase Auth for other users with the client token
            # We'll use the email stored in the board data if available
            member_email = ""
            if member_id.startswith("user_"):
                # This is a user added by email, extract the email
                member_email = member_id.replace("user_", "").replace("_at_", "@").replace("_dot_", ".")
                members_data.append({
                    "id": member_id,
                    "email": member_email,
                    "display_name": member_email
                })
            else:
                # Try to get user info from Firebase Auth
                # This might not work for other users with the client token
                members_data.append({
                    "id": member_id,
                    "email": f"user-{member_id}@example.com",  # Placeholder
                    "display_name": f"User {member_id}"  # Placeholder
                })
        except Exception as e:
            print(f"Error fetching member {member_id}: {e}")
            members_data.append({
                "id": member_id,
                "email": f"user-{member_id}@example.com",  # Placeholder
                "display_name": f"User {member_id}"  # Placeholder
            })
    
    # Replace member IDs with detailed member info
    board_data["members_info"] = members_data
    
    # Directly query the tasks subcollection
    tasks_url = f"{FIRESTORE_BASE_URL}/boards/{board_id}/tasks"
    tasks_response = requests.get(tasks_url)

    print(f"tasks_response: {tasks_response} ");
    
    tasks = []
    if tasks_response.status_code == 200:
        # For list responses, the documents are in a "documents" array
        if "documents" in tasks_response.json():
            for doc in tasks_response.json()["documents"]:
                task_data = firestore_doc_to_dict(doc)
                if task_data:
                    # Add assignee details if task is assigned
                    if task_data.get("assigned_to"):
                        try:
                            assignee_id = task_data["assigned_to"]
                            # Check if this is the current user
                            if assignee_id == user["id"]:
                                task_data["assignee_info"] = {
                                    "id": user["id"],
                                    "email": user["email"],
                                    "display_name": user["email"]  # Use email as display name
                                }
                            # Check if this is a user added by email
                            elif assignee_id.startswith("user_"):
                                assignee_email = assignee_id.replace("user_", "").replace("_at_", "@").replace("_dot_", ".")
                                task_data["assignee_info"] = {
                                    "id": assignee_id,
                                    "email": assignee_email,
                                    "display_name": assignee_email
                                }
                            # Otherwise use a placeholder
                            else:
                                task_data["assignee_info"] = {
                                    "id": assignee_id,
                                    "email": f"user-{assignee_id}@example.com",  # Placeholder
                                    "display_name": f"User {assignee_id}"  # Placeholder
                                }
                        except Exception as e:
                            print(f"Error fetching assignee {task_data['assigned_to']}: {e}")
                tasks.append(task_data)
    
    # Also add creator info
    try:
        creator_id = board_data["creator_id"]
        # Check if creator is current user
        if creator_id == user["id"]:
            board_data["creator_info"] = {
                "id": user["id"],
                "email": user["email"],
                "display_name": user["email"]  # Use email as display name
            }
        else:
            # Use creator email from board data
            creator_email = board_data.get("creator_email", f"creator-{creator_id}@example.com")
            board_data["creator_info"] = {
                "id": creator_id,
                "email": creator_email,
                "display_name": creator_email
            }
    except Exception as e:
        print(f"Error fetching creator {board_data['creator_id']}: {e}")
    
    return {"board": board_data, "tasks": tasks}

@app.put("/api/boards/{board_id}")
async def update_board(board_id: str, data: dict = Body(...), user: dict = Depends(get_current_user)):
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Get board data
    response = requests.get(f"{FIRESTORE_BASE_URL}/boards/{board_id}")
    
    if response.status_code != 200:
        raise HTTPException(status_code=404, detail="Board not found")
    
    board_data = firestore_doc_to_dict(response.json())
    
    # Only creator can update board title
    if user["id"] != board_data.get("creator_id"):
        raise HTTPException(status_code=403, detail="Only the board creator can update the board")
    
    # Update board title
    if "title" in data:
        update_data = {
            "fields": {
                "title": {"stringValue": data["title"]}
            }
        }
        
        update_response = requests.patch(
            f"{FIRESTORE_BASE_URL}/boards/{board_id}?updateMask.fieldPaths=title",
            json=update_data
        )
        
        if update_response.status_code != 200:
            raise HTTPException(status_code=update_response.status_code, detail=update_response.text)
    
    return {"success": True}

@app.delete("/api/boards/{board_id}")
async def delete_board(board_id: str, user: dict = Depends(get_current_user)):
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Get board data
    response = requests.get(f"{FIRESTORE_BASE_URL}/boards/{board_id}")
    
    if response.status_code != 200:
        raise HTTPException(status_code=404, detail="Board not found")
    
    board_data = firestore_doc_to_dict(response.json())
    
    # Only creator can delete board
    if user["id"] != board_data.get("creator_id"):
        raise HTTPException(status_code=403, detail="Only the board creator can delete the board")
    
    # Check if there are any members
    if board_data.get("members", []):
        raise HTTPException(status_code=400, detail="Cannot delete board with members")
    
    # Check if there are any tasks
    tasks_query = {
        "structuredQuery": {
            "from": [{"collectionId": f"boards/{board_id}/tasks"}],
            "limit": 1
        }
    }
    
    tasks_response = requests.post(
        FIRESTORE_QUERY_URL,
        json=tasks_query
    )
    
    if any("document" in doc for doc in tasks_response.json()):
        raise HTTPException(status_code=400, detail="Cannot delete board with tasks")
    
    # Delete board
    delete_response = requests.delete(f"{FIRESTORE_BASE_URL}/boards/{board_id}")
    
    if delete_response.status_code != 200:
        raise HTTPException(status_code=delete_response.status_code, detail=delete_response.text)
    
    return {"success": True}

# API endpoints for board members
@app.post("/api/boards/{board_id}/members")
async def add_member(board_id: str, data: dict = Body(...), user: dict = Depends(get_current_user)):
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    email = data.get("email")
    if not email:
        raise HTTPException(status_code=400, detail="Member email is required")
    
    # Get board data
    response = requests.get(f"{FIRESTORE_BASE_URL}/boards/{board_id}")
    
    if response.status_code != 200:
        raise HTTPException(status_code=404, detail="Board not found")
    
    board_data = firestore_doc_to_dict(response.json())
    
    # Only creator can add members
    if user["id"] != board_data.get("creator_id"):
        raise HTTPException(status_code=403, detail="Only the board creator can add members")
    
    # Find user by email
    try:
        # We need to query Firebase Auth for user by email
        # This requires admin SDK which we don't have
        # For this implementation, we'll use a workaround
        # We'll assume the email exists and belongs to a user
        # In a real implementation, you'd need to verify this
        
        # For demo purposes, we'll use a placeholder user ID
        # In a real app, you'd need to look up the user ID from Firebase Auth
        member_id = "user_" + email.replace("@", "_at_").replace(".", "_dot_")
        
        # Don't add if already a member or creator
        if member_id == board_data.get("creator_id") or member_id in board_data.get("members", []):
            raise HTTPException(status_code=400, detail="User is already a member of this board")
        
        # Add member to board
        members = board_data.get("members", [])
        members.append(member_id)
        
        update_data = {
            "fields": {
                "members": {"arrayValue": {"values": [{"stringValue": m} for m in members]}}
            }
        }
        
        update_response = requests.patch(
            f"{FIRESTORE_BASE_URL}/boards/{board_id}?updateMask.fieldPaths=members",
            json=update_data
        )
        
        if update_response.status_code != 200:
            raise HTTPException(status_code=update_response.status_code, detail=update_response.text)
        
        return {"success": True, "member_id": member_id, "email": email}
    except Exception as e:
        print(f"Error adding member: {e}")
        raise HTTPException(status_code=404, detail="User not found")

@app.delete("/api/boards/{board_id}/members/{member_id}")
async def remove_member(board_id: str, member_id: str, user: dict = Depends(get_current_user)):
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Get board data
    response = requests.get(f"{FIRESTORE_BASE_URL}/boards/{board_id}")
    
    if response.status_code != 200:
        raise HTTPException(status_code=404, detail="Board not found")
    
    board_data = firestore_doc_to_dict(response.json())
    
    # Only creator can remove members
    if user["id"] != board_data.get("creator_id"):
        raise HTTPException(status_code=403, detail="Only the board creator can remove members")
    
    # Check if member exists
    if member_id not in board_data.get("members", []):
        raise HTTPException(status_code=404, detail="Member not found")
    
    # Remove member from board
    members = board_data.get("members", [])
    members.remove(member_id)
    
    update_data = {
        "fields": {
            "members": {"arrayValue": {"values": [{"stringValue": m} for m in members]}}
        }
    }
    
    update_response = requests.patch(
        f"{FIRESTORE_BASE_URL}/boards/{board_id}?updateMask.fieldPaths=members",
        json=update_data
    )
    
    if update_response.status_code != 200:
        raise HTTPException(status_code=update_response.status_code, detail=update_response.text)
    
    # Mark all tasks assigned to this member as unassigned
    tasks_query = {
        "structuredQuery": {
            "from": [{"collectionId": f"boards/{board_id}/tasks"}],
            "where": {
                "fieldFilter": {
                    "field": {"fieldPath": "assigned_to"},
                    "op": "EQUAL",
                    "value": {"stringValue": member_id}
                }
            }
        }
    }
    
    tasks_response = requests.post(
        FIRESTORE_QUERY_URL,
        json=tasks_query
    )
    
    for doc in tasks_response.json():
        if "document" in doc:
            task_path = doc["document"]["name"]
            task_id = task_path.split("/")[-1]
            
            update_task_data = {
                "fields": {
                    "assigned_to": {"stringValue": ""},
                    "unassigned": {"booleanValue": True}
                }
            }
            
            requests.patch(
                f"{task_path}?updateMask.fieldPaths=assigned_to&updateMask.fieldPaths=unassigned",
                json=update_task_data
            )
    
    return {"success": True}

# API endpoints for tasks
@app.get("/api/boards/{board_id}/tasks")
async def get_board_tasks(board_id: str, user: dict = Depends(get_current_user)):
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Verify board access
    board_response = requests.get(f"{FIRESTORE_BASE_URL}/boards/{board_id}")
    if board_response.status_code != 200:
        raise HTTPException(status_code=404, detail="Board not found")
    
    board_data = firestore_doc_to_dict(board_response.json())
    if user["id"] != board_data.get("creator_id") and user["id"] not in board_data.get("members", []):
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Directly query the tasks subcollection
    tasks_url = f"{FIRESTORE_BASE_URL}/boards/{board_id}/tasks"
    tasks_response = requests.get(tasks_url)
    
    tasks = []
    if tasks_response.status_code == 200:
        # For list responses, the documents are in a "documents" array
        if "documents" in tasks_response.json():
            for doc in tasks_response.json()["documents"]:
                task_data = firestore_doc_to_dict(doc)
                if task_data:
                    tasks.append(task_data)
    
    return {"tasks": tasks}

@app.post("/api/boards/{board_id}/tasks")
async def create_task(board_id: str, data: dict = Body(...), user: dict = Depends(get_current_user)):
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    title = data.get("title")
    due_date = data.get("due_date")
    assigned_to = data.get("assigned_to", "")
    
    if not title:
        raise HTTPException(status_code=400, detail="Task title is required")
    
    # Get board data
    response = requests.get(f"{FIRESTORE_BASE_URL}/boards/{board_id}")
    
    if response.status_code != 200:
        raise HTTPException(status_code=404, detail="Board not found")
    
    board_data = firestore_doc_to_dict(response.json())
    
    # Check if user has access
    if user["id"] != board_data.get("creator_id") and user["id"] not in board_data.get("members", []):
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Check if task with same title already exists
    tasks_query = {
        "structuredQuery": {
            "from": [{"collectionId": f"boards/{board_id}/tasks"}],
            "where": {
                "fieldFilter": {
                    "field": {"fieldPath": "title"},
                    "op": "EQUAL",
                    "value": {"stringValue": title}
                }
            }
        }
    }
    
    tasks_response = requests.post(
        FIRESTORE_QUERY_URL,
        json=tasks_query
    )
    
    if any("document" in doc for doc in tasks_response.json()):
        raise HTTPException(status_code=400, detail="Task with this title already exists")
    
    # Create new task
    task_data = {
        "title": title,
        "due_date": due_date or "",
        "assigned_to": assigned_to or "",
        "completed": False,
        "created_by": user["id"],
        "created_at": datetime.now().isoformat(),
        "unassigned": not assigned_to
    }
    
    new_task = {
        "fields": dict_to_firestore_fields(task_data)
    }
    
    # Make sure we're using the correct path for the tasks subcollection
    task_response = requests.post(
        f"{FIRESTORE_BASE_URL}/boards/{board_id}/tasks",
        json=new_task
    )
    
    if task_response.status_code != 200:
        print(f"Error creating task: {task_response.text}")
        raise HTTPException(status_code=task_response.status_code, detail=task_response.text)
    
    task_data_response = task_response.json()
    task_id = task_data_response["name"].split("/")[-1]
    
    return {
        "id": task_id,
        **task_data
    }

@app.put("/api/boards/{board_id}/tasks/{task_id}")
async def update_task(board_id: str, task_id: str, data: dict = Body(...), user: dict = Depends(get_current_user)):
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Get board data
    board_response = requests.get(f"{FIRESTORE_BASE_URL}/boards/{board_id}")
    
    if board_response.status_code != 200:
        raise HTTPException(status_code=404, detail="Board not found")
    
    board_data = firestore_doc_to_dict(board_response.json())
    
    # Check if user has access
    if user["id"] != board_data.get("creator_id") and user["id"] not in board_data.get("members", []):
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Get task data
    task_response = requests.get(f"{FIRESTORE_BASE_URL}/boards/{board_id}/tasks/{task_id}")
    
    if task_response.status_code != 200:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task_data = firestore_doc_to_dict(task_response.json())
    
    # Check if user has permission to update the task
    is_board_creator = user["id"] == board_data.get("creator_id")
    is_task_creator = user["id"] == task_data.get("created_by")
    
    if not (is_board_creator or is_task_creator):
        raise HTTPException(status_code=403, detail="You don't have permission to update this task")
    
    update_fields = {}
    update_mask_paths = []
    
    # Update task fields
    if "title" in data:
        update_fields["title"] = {"stringValue": data["title"]}
        update_mask_paths.append("title")
    
    if "due_date" in data:
        update_fields["due_date"] = {"stringValue": data["due_date"]}
        update_mask_paths.append("due_date")
    
    if "assigned_to" in data:
        update_fields["assigned_to"] = {"stringValue": data["assigned_to"]}
        update_mask_paths.append("assigned_to")
        
        # If task was previously unassigned and now has an assignee, remove the unassigned flag
        if data["assigned_to"] and task_data.get("unassigned", False):
            update_fields["unassigned"] = {"booleanValue": False}
            update_mask_paths.append("unassigned")
    
    if "completed" in data:
        update_fields["completed"] = {"booleanValue": data["completed"]}
        update_mask_paths.append("completed")
        
        if data["completed"]:
            update_fields["completed_at"] = {"stringValue": datetime.now().isoformat()}
            update_mask_paths.append("completed_at")
        else:
            update_fields["completed_at"] = {"nullValue": None}
            update_mask_paths.append("completed_at")
    
    if not update_fields:
        return {"success": True}
    
    # Build update mask query parameter
    update_mask = "&".join([f"updateMask.fieldPaths={path}" for path in update_mask_paths])
    
    update_data = {
        "fields": update_fields
    }
    
    update_response = requests.patch(
        f"{FIRESTORE_BASE_URL}/boards/{board_id}/tasks/{task_id}?{update_mask}",
        json=update_data
    )
    
    if update_response.status_code != 200:
        raise HTTPException(status_code=update_response.status_code, detail=update_response.text)
    
    return {"success": True}

@app.delete("/api/boards/{board_id}/tasks/{task_id}")
async def delete_task(board_id: str, task_id: str, user: dict = Depends(get_current_user)):
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Get board data
    board_response = requests.get(f"{FIRESTORE_BASE_URL}/boards/{board_id}")
    
    if board_response.status_code != 200:
        raise HTTPException(status_code=404, detail="Board not found")
    
    board_data = firestore_doc_to_dict(board_response.json())
    
    # Check if user has access to this board
    if user["id"] != board_data.get("creator_id") and user["id"] not in board_data.get("members", []):
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Get task data
    task_response = requests.get(f"{FIRESTORE_BASE_URL}/boards/{board_id}/tasks/{task_id}")
    
    if task_response.status_code != 200:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task_data = firestore_doc_to_dict(task_response.json())
    
    # Enhanced authorization check:
    # Only allow deletion if user is:
    # 1. The board creator, OR
    # 2. The task creator
    is_board_creator = user["id"] == board_data.get("creator_id")
    is_task_creator = user["id"] == task_data.get("created_by")
    
    if not (is_board_creator or is_task_creator):
        raise HTTPException(status_code=403, detail="You don't have permission to delete this task")
    
    # Delete task
    delete_response = requests.delete(f"{FIRESTORE_BASE_URL}/boards/{board_id}/tasks/{task_id}")
    
    if delete_response.status_code != 200:
        raise HTTPException(status_code=delete_response.status_code, detail=delete_response.text)
    
    return {"success": True}

@app.get("/api/users/search")
async def search_users(query: str, user: dict = Depends(get_current_user)):
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # This is a simplified approach - in a real app, you'd need more robust user search
    # For demo purposes, we'll just return a placeholder user
    # In a real implementation, you'd need to query Firebase Auth for users
    
    # For demo purposes, we'll create a placeholder user
    placeholder_user = {
        "id": "user_" + query.replace("@", "_at_").replace(".", "_dot_"),
        "email": query,
        "display_name": query
    }
    
    return {"users": [placeholder_user]}

@app.get("/api/task-stats/{board_id}")
async def get_task_stats(board_id: str, user: dict = Depends(get_current_user)):
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Get board data
    board_response = requests.get(f"{FIRESTORE_BASE_URL}/boards/{board_id}")
    
    if board_response.status_code != 200:
        raise HTTPException(status_code=404, detail="Board not found")
    
    board_data = firestore_doc_to_dict(board_response.json())
    
    # Check if user has access
    if user["id"] != board_data.get("creator_id") and user["id"] not in board_data.get("members", []):
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Get all tasks
    tasks_query = {
        "structuredQuery": {
            "from": [{"collectionId": f"boards/{board_id}/tasks"}]
        }
    }
    
    tasks_response = requests.post(
        FIRESTORE_QUERY_URL,
        json=tasks_query
    )
    
    total_tasks = 0
    completed_tasks = 0
    active_tasks = 0
    
    for doc in tasks_response.json():
        if "document" in doc:
            total_tasks += 1
            task_data = firestore_doc_to_dict(doc["document"])
            if task_data.get("completed", False):
                completed_tasks += 1
            else:
                active_tasks += 1
    
    return {
        "total_tasks": total_tasks,
        "completed_tasks": completed_tasks,
        "active_tasks": active_tasks
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
