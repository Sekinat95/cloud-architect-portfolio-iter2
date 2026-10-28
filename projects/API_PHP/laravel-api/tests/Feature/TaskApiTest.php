<?php

namespace Tests\Feature;

use Illuminate\Foundation\Testing\RefreshDatabase;
use Tests\TestCase;

class TaskApiTest extends TestCase
{
    use RefreshDatabase;

    public function test_can_create_a_task(): void
    {
        $response = $this->postJson('/api/tasks', [
            'title' => 'Learn Laravel testing',
            'completed' => true,
        ]);

        $response->assertStatus(201);

        $response->assertJsonFragment([
            'title' => 'Learn Laravel testing',
            'completed' => true,
        ]);

        $this->assertDatabaseHas('tasks', [
            'title' => 'Learn Laravel testing',
            'completed' => true,
        ]);
    }


    public function test_can_get_all_tasks(): void
    {
        // Arrange: create two tasks in the test database
        \App\Models\Task::create([
            'title' => 'First task',
            'completed' => false,
        ]);

        \App\Models\Task::create([
            'title' => 'Second task',
            'completed' => true,
        ]);

        // Act: send a GET request to the API
        $response = $this->getJson('/api/tasks');

        // Assert: verify the response
        $response->assertStatus(200);

        $response->assertJsonCount(2);

        $response->assertJsonFragment([
            'title' => 'First task',
            'completed' => false,
        ]);

        $response->assertJsonFragment([
            'title' => 'Second task',
            'completed' => true,
        ]);
    }


    public function test_can_get_a_single_task(): void
    {
        // Arrange: create a task in the test database
        $task = \App\Models\Task::create([
            'title' => 'Learn Laravel route model binding',
            'completed' => false,
        ]);

        // Act: retrieve the task by its ID
        $response = $this->getJson("/api/tasks/{$task->id}");

        // Assert: verify the HTTP response
        $response->assertStatus(200);

        $response->assertJsonPath('id', $task->id);

        $response->assertJsonPath(
            'title',
            'Learn Laravel route model binding'
        );

        $response->assertJsonPath('completed', false);
    }

    public function test_can_update_a_task(): void
    {
        // Arrange: create a task
        $task = \App\Models\Task::create([
            'title' => 'Original task',
            'completed' => false,
        ]);

        // Act: update the task through the API
        $response = $this->patchJson("/api/tasks/{$task->id}", [
            'title' => 'Updated task',
            'completed' => true,
        ]);

        // Assert: verify the HTTP response
        $response->assertStatus(200);

        // Verify the JSON response
        $response->assertJsonPath('title', 'Updated task');
        $response->assertJsonPath('completed', true);

        // Verify the changes were saved to the database
        $this->assertDatabaseHas('tasks', [
            'id' => $task->id,
            'title' => 'Updated task',
            'completed' => true,
        ]);
    }


    public function test_can_delete_a_task(): void
    {
        // Arrange: create a task
        $task = \App\Models\Task::create([
            'title' => 'Task to delete',
            'completed' => false,
        ]);

        // Act: send a DELETE request
        $response = $this->deleteJson("/api/tasks/{$task->id}");

        // Assert: verify HTTP 204 No Content
        $response->assertNoContent();

        // Assert: verify the task no longer exists
        $this->assertDatabaseMissing('tasks', [
            'id' => $task->id,
        ]);
    }

    public function test_returns_404_when_task_does_not_exist(): void
    {
        // Act: request a task that doesn't exist
        $response = $this->getJson('/api/tasks/999999');

        // Assert: Laravel returns HTTP 404
        $response->assertNotFound();
    }

    public function test_cannot_create_task_without_title(): void
    {
        // Act: send a POST request without a title
        $response = $this->postJson('/api/tasks', [
            'completed' => false,
        ]);

        // Assert: Laravel rejects invalid input
        $response->assertStatus(422);

        // Assert: the validation error concerns the title
        $response->assertJsonValidationErrors(['title']);

        // Assert: no task was created
        $this->assertDatabaseCount('tasks', 0);
    }
}