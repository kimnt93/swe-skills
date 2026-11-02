// Command archcheck enforces the go-code layering on imports, so a change cannot breach the
// architecture: interfaces -> application -> domain, adapters implement ports, and only the
// composition root (bootstrap, cmd, e2e) wires everything together.
//
//	go run ./scripts/archcheck <module-root>   exit 0 = clean, 1 = breaches
//
// Rules, by the first directory under internal/ (anything else is unrestricted):
//
//	domain          may import only internal/domain; no I/O packages (net/http, database/sql, os,
//	                the Postgres, Redis, Kafka, S3 and Fiber clients)
//	application     may import domain, application
//	infrastructure  may import domain, application, config, logger, models, infrastructure
//	interfaces      may import domain, application, config, logger, models, interfaces
//	config, logger, models   may import only themselves
//	bootstrap, e2e  may import anything (composition root and end-to-end tests)
package main

import (
	"bufio"
	"fmt"
	"go/parser"
	"go/token"
	"io/fs"
	"os"
	"path/filepath"
	"sort"
	"strconv"
	"strings"
)

var allowed = map[string][]string{
	"domain":         {"domain"},
	"application":    {"domain", "application"},
	"infrastructure": {"domain", "application", "config", "logger", "models", "infrastructure"},
	"interfaces":     {"domain", "application", "config", "logger", "models", "interfaces"},
	"config":         {"config"},
	"logger":         {"logger"},
	"models":         {"models"},
}

var domainForbidden = []string{
	"net/http", "database/sql", "os", "os/exec",
	"github.com/go-pg/", "github.com/jackc/", "github.com/uptrace/bun",
	"github.com/redis/", "github.com/confluentinc/", "github.com/aws/", "github.com/gofiber/",
}

// Breach is one import that crosses the architecture.
type Breach struct {
	File   string
	Line   int
	Layer  string
	Import string
	Reason string
}

func main() {
	if len(os.Args) != 2 {
		fmt.Fprintln(os.Stderr, "usage: archcheck <module-root>")
		os.Exit(2)
	}
	breaches, err := Check(os.Args[1])
	if err != nil {
		fmt.Fprintln(os.Stderr, "archcheck:", err)
		os.Exit(2)
	}
	for _, b := range breaches {
		fmt.Printf("%s:%d: %s imports %s: %s\n", b.File, b.Line, b.Layer, b.Import, b.Reason)
	}
	if len(breaches) > 0 {
		os.Exit(1)
	}
}

// Check returns every breach under root/internal, given the module path in root/go.mod.
func Check(root string) ([]Breach, error) {
	module, err := modulePath(filepath.Join(root, "go.mod"))
	if err != nil {
		return nil, err
	}
	internal := filepath.Join(root, "internal")
	var breaches []Breach
	fset := token.NewFileSet()
	err = filepath.WalkDir(internal, func(path string, d fs.DirEntry, err error) error {
		if err != nil {
			return err
		}
		if d.IsDir() || !strings.HasSuffix(path, ".go") || strings.HasSuffix(path, "_test.go") {
			return nil
		}
		rel, err := filepath.Rel(internal, path)
		if err != nil {
			return err
		}
		layer := strings.Split(filepath.ToSlash(rel), "/")[0]
		rules, restricted := allowed[layer]
		if !restricted {
			return nil
		}
		file, err := parser.ParseFile(fset, path, nil, parser.ImportsOnly)
		if err != nil {
			return err
		}
		for _, spec := range file.Imports {
			imported, _ := strconv.Unquote(spec.Path.Value)
			line := fset.Position(spec.Pos()).Line
			if reason := judge(module, layer, rules, imported); reason != "" {
				breaches = append(breaches, Breach{File: path, Line: line, Layer: layer, Import: imported, Reason: reason})
			}
		}
		return nil
	})
	sort.Slice(breaches, func(i, j int) bool {
		if breaches[i].File != breaches[j].File {
			return breaches[i].File < breaches[j].File
		}
		return breaches[i].Line < breaches[j].Line
	})
	return breaches, err
}

func judge(module, layer string, rules []string, imported string) string {
	prefix := module + "/internal/"
	if strings.HasPrefix(imported, prefix) {
		target := strings.Split(strings.TrimPrefix(imported, prefix), "/")[0]
		for _, ok := range rules {
			if target == ok {
				return ""
			}
		}
		return fmt.Sprintf("%s may import only %s", layer, strings.Join(rules, ", "))
	}
	if layer != "domain" {
		return ""
	}
	for _, bad := range domainForbidden {
		if imported == bad || strings.HasSuffix(bad, "/") && strings.HasPrefix(imported, bad) || strings.HasPrefix(imported, bad+"/") {
			return "the domain does no I/O: put it behind a port in application and implement it in infrastructure"
		}
	}
	return ""
}

func modulePath(goMod string) (string, error) {
	f, err := os.Open(goMod)
	if err != nil {
		return "", err
	}
	defer f.Close()
	scanner := bufio.NewScanner(f)
	for scanner.Scan() {
		line := strings.TrimSpace(scanner.Text())
		if strings.HasPrefix(line, "module ") {
			return strings.TrimSpace(strings.TrimPrefix(line, "module ")), nil
		}
	}
	return "", fmt.Errorf("%s has no module line", goMod)
}
