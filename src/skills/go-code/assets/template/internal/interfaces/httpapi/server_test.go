package httpapi

import (
	"context"
	"encoding/json"
	"errors"
	"io"
	"net/http"
	"net/http/httptest"
	"regexp"
	"strings"
	"testing"
	"time"

	"github.com/gofiber/fiber/v3"

	"example.com/service/internal/application"
	"example.com/service/internal/domain/item"
	"example.com/service/internal/interfaces/httpapi/middleware"
)

type fakeRepo struct {
	items map[string]item.Item
}

func (f *fakeRepo) Create(_ context.Context, it item.Item) error { f.items[it.ID] = it; return nil }
func (f *fakeRepo) Get(_ context.Context, id string) (item.Item, error) {
	it, ok := f.items[id]
	if !ok {
		return item.Item{}, application.ErrNotFound
	}
	return it, nil
}

type fakeEvents struct {
	published []string
}

func (f *fakeEvents) Publish(_ context.Context, topic, key string, _ []byte) error {
	f.published = append(f.published, topic+"/"+key)
	return nil
}

func newTestApp(t *testing.T) (*fiber.App, *fakeEvents) {
	t.Helper()
	ev := &fakeEvents{}

	svc := application.Items{
		Repo:   &fakeRepo{items: map[string]item.Item{}},
		Events: ev,
		NewID: func() string {
			return "id-1"
		},
		Now: func() time.Time {
			return time.Date(2026, 1, 2, 3, 4, 5, 0, time.UTC)
		},
	}

	return NewApp(testOptions(nil), svc), ev
}

func testOptions(checks []Checker) Options {
	return Options{
		InternalServiceToken: "tok",
		Identity: Identity{
			ServiceName:    "svc",
			EnvName:        "stg",
			NodeName:       "node-1",
			ServiceVersion: "1.2.3",
			StartedAt:      time.Now().Add(-90 * time.Second),
			Config:         map[string]any{"port": 3000, "log_level": "info"},
		},
		Checks: checks,
	}
}

func do(t *testing.T, app *fiber.App, method, path, body, token string) (int, map[string]any) {
	t.Helper()
	ctx := context.Background()
	req := httptest.NewRequestWithContext(ctx, method, path, strings.NewReader(body))
	req.Header.Set("Content-Type", "application/json")
	if token != "" {
		req.Header.Set("x-internal-service-token", token)
	}
	res, err := app.Test(req, fiber.TestConfig{Timeout: 5 * time.Second, FailOnTimeout: true})
	if err != nil {
		t.Fatal(err)
	}
	defer res.Body.Close()
	raw, _ := io.ReadAll(res.Body)
	var out map[string]any
	_ = json.Unmarshal(raw, &out)
	return res.StatusCode, out
}

func TestItemsAPI(t *testing.T) {
	app, ev := newTestApp(t)
	for _, tc := range []struct {
		name, method, path, body, token string
		status                          int
		code                            string
	}{
		{"no token", "POST", "/v1/items", `{"name":"pen"}`, "", 401, "unauthorized"},
		{"created", "POST", "/v1/items", `{"name":"pen"}`, "tok", 201, ""},
		{"invalid name", "POST", "/v1/items", `{"name":"  "}`, "tok", 422, "validation_error"},
		{"bad json", "POST", "/v1/items", `{`, "tok", 400, "invalid_json"},
		{"found", "GET", "/v1/items/id-1", "", "tok", 200, ""},
		{"missing", "GET", "/v1/items/nope", "", "tok", 404, "not_found"},
		{"unknown route", "GET", "/nope", "", "", 404, "not_found"},
	} {
		t.Run(tc.name, func(t *testing.T) {
			status, out := do(t, app, tc.method, tc.path, tc.body, tc.token)
			if status != tc.status {
				t.Fatalf("status = %d, want %d (%v)", status, tc.status, out)
			}
			if tc.code != "" {
				if e, _ := out["error"].(map[string]any); e["code"] != tc.code {
					t.Fatalf("error = %v, want code %s", out["error"], tc.code)
				}
			}
		})
	}
	if len(ev.published) != 1 || ev.published[0] != "items.created/id-1" {
		t.Fatalf("events = %v", ev.published)
	}
}

type reply struct {
	status int
	header http.Header
	body   []byte
}

func get(t *testing.T, app *fiber.App, path string) reply {
	t.Helper()
	req := httptest.NewRequestWithContext(context.Background(), "GET", path, nil)
	res, err := app.Test(req, fiber.TestConfig{Timeout: 5 * time.Second, FailOnTimeout: true})
	if err != nil {
		t.Fatal(err)
	}
	defer res.Body.Close()
	raw, _ := io.ReadAll(res.Body)

	return reply{status: res.StatusCode, header: res.Header, body: raw}
}

func TestHealthzIsOpenAndNamesTheService(t *testing.T) {
	app, _ := newTestApp(t)
	res := get(t, app, "/healthz")
	raw := res.body
	if res.status != 200 || res.header.Get("Cache-Control") != "no-store" {
		t.Fatalf("healthz = %d, cache-control %q", res.status, res.header.Get("Cache-Control"))
	}

	var body map[string]any
	if err := json.Unmarshal(raw, &body); err != nil {
		t.Fatal(err)
	}
	for _, key := range []string{
		"status", "service_name", "env_name", "node_name", "api_versions", "service_version",
		"started_at", "checked_at", "uptime_seconds", "config", "checks",
	} {
		if _, ok := body[key]; !ok {
			t.Fatalf("healthz is missing %q: %s", key, raw)
		}
	}
	if body["status"] != "ok" || body["service_name"] != "svc" || body["env_name"] != "stg" ||
		body["node_name"] != "node-1" {
		t.Fatalf("identity fields: %s", raw)
	}
	if versions := body["api_versions"].([]any); len(versions) != 1 || versions[0] != "v1" {
		t.Fatalf("api_versions: %s", raw)
	}
	cfg := body["config"].(map[string]any)
	if cfg["port"] != float64(3000) || cfg["docs_url"] != "/docs" {
		t.Fatalf("config: %v", cfg)
	}
	if checks := body["checks"].([]any); len(checks) != 0 {
		t.Fatalf("checks should be an empty list: %v", checks)
	}
}

func TestHealthzReportsDownWithoutLeaking(t *testing.T) {
	down := Checker{Name: "postgres", Ping: func(context.Context) error {
		return errors.New("dial postgres://u:secret@pg: refused")
	}}
	up := Checker{Name: "redis", Ping: func(context.Context) error { return nil }}
	svc := application.Items{Repo: &fakeRepo{items: map[string]item.Item{}}}
	app := NewApp(testOptions([]Checker{down, up}), svc)

	res := get(t, app, "/healthz")
	if res.status != 503 {
		t.Fatalf("status = %d, want 503", res.status)
	}
	if strings.Contains(string(res.body), "secret") {
		t.Fatalf("healthz leaked the error text: %s", res.body)
	}

	var body Health
	if err := json.Unmarshal(res.body, &body); err != nil {
		t.Fatal(err)
	}
	if body.Status != "down" || body.Checks[0].Error != "unavailable" {
		t.Fatalf("checks: %+v", body.Checks)
	}
	if body.Checks[1].Status != "ok" {
		t.Fatalf("the healthy dependency must stay ok: %+v", body.Checks)
	}
}

func TestHealthIsOneUnversionedEndpoint(t *testing.T) {
	app, _ := newTestApp(t)
	// /v1 needs the token, so an unknown path there answers 401 before it could answer 404.
	for _, path := range []string{"/v1/healthz", "/readyz"} {
		if res := get(t, app, path); res.status == 200 {
			t.Fatalf("%s = 200: health is /healthz only", path)
		}
	}
}

// internalGet calls /internal with the given headers.
func internalGet(t *testing.T, app *fiber.App, headers map[string]string) reply {
	t.Helper()
	req := httptest.NewRequestWithContext(context.Background(), "GET", "/internal", nil)
	for key, value := range headers {
		req.Header.Set(key, value)
	}
	res, err := app.Test(req, fiber.TestConfig{Timeout: 5 * time.Second, FailOnTimeout: true})
	if err != nil {
		t.Fatal(err)
	}
	defer res.Body.Close()
	raw, _ := io.ReadAll(res.Body)

	return reply{status: res.StatusCode, header: res.Header, body: raw}
}

func TestInternalNeedsTheToken(t *testing.T) {
	app, _ := newTestApp(t)
	for _, headers := range []map[string]string{nil, {"x-internal-service-token": "wrong"}} {
		if res := internalGet(t, app, headers); res.status != 401 {
			t.Fatalf("/internal with %v = %d, want 401", headers, res.status)
		}
	}
}

func TestInternalShowsHealthAndTheCaller(t *testing.T) {
	app, _ := newTestApp(t)
	res := internalGet(t, app, map[string]string{
		"x-internal-service-token": "tok", "x-user-id": "u-7", "x-username": "linh",
	})
	if res.status != 200 || res.header.Get("Cache-Control") != "no-store" {
		t.Fatalf("/internal = %d", res.status)
	}
	var body InternalHealth
	if err := json.Unmarshal(res.body, &body); err != nil {
		t.Fatal(err)
	}
	if body.Status != "ok" || body.ServiceName != "svc" ||
		body.Caller != (middleware.Caller{UserID: "u-7", Username: "linh"}) {
		t.Fatalf("body: %s", res.body)
	}

	empty := internalGet(t, app, map[string]string{"x-internal-service-token": "tok"})
	if !strings.Contains(string(empty.body), `"caller":{"user_id":"","username":""}`) {
		t.Fatalf("caller must be present and empty: %s", empty.body)
	}
}

func TestTokenMayCarryABearerPrefix(t *testing.T) {
	app, _ := newTestApp(t)
	for _, value := range []string{"Bearer tok", "bearer tok", "  Bearer   tok "} {
		res := internalGet(t, app, map[string]string{"x-internal-service-token": value})
		if res.status != 200 {
			t.Fatalf("token %q = %d, want 200", value, res.status)
		}
	}
	if status, _ := do(t, app, "GET", "/v1/items/id-1", "", "Bearer tok"); status == 401 {
		t.Fatal("/v1 must accept the Bearer form too")
	}
}

func TestInternalReportsDownWithoutLeaking(t *testing.T) {
	down := Checker{Name: "postgres", Ping: func(context.Context) error {
		return errors.New("dial postgres://u:secret@pg: refused")
	}}
	svc := application.Items{Repo: &fakeRepo{items: map[string]item.Item{}}}
	app := NewApp(testOptions([]Checker{down}), svc)

	res := internalGet(t, app, map[string]string{"x-internal-service-token": "tok"})
	if res.status != 503 || strings.Contains(string(res.body), "secret") {
		t.Fatalf("/internal = %d: %s", res.status, res.body)
	}
}

func TestDocsArePublic(t *testing.T) {
	app, _ := newTestApp(t)
	page := get(t, app, "/docs")
	if page.status != 200 || !strings.Contains(string(page.body), "swagger-ui") {
		t.Fatalf("/docs = %d", page.status)
	}
	if spec := get(t, app, "/docs/openapi.json"); spec.status != 200 {
		t.Fatalf("/docs/openapi.json = %d", spec.status)
	}
}

// TestSwaggerListsEveryRoute fails when a route is missing from the committed spec: run
// `make swagger` and commit the result.
func TestSwaggerListsEveryRoute(t *testing.T) {
	var spec struct {
		Paths map[string]map[string]any `json:"paths"`
	}
	if err := json.Unmarshal(openapiSpec, &spec); err != nil {
		t.Fatal(err)
	}

	app, _ := newTestApp(t)
	for _, route := range app.GetRoutes(true) {
		if strings.HasPrefix(route.Path, "/docs") || route.Method == "HEAD" {
			continue
		}
		path := regexp.MustCompile(`:(\w+)`).ReplaceAllString(route.Path, "{$1}")
		if _, ok := spec.Paths[path][strings.ToLower(route.Method)]; !ok {
			t.Errorf("%s %s is not in openapi/swagger.json: run make swagger", route.Method, path)
		}
	}
}
