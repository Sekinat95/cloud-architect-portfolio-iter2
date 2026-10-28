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
}