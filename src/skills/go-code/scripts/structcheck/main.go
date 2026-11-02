// Command structcheck enforces the go-code rule for data structs: no pointer fields and no
// omitempty, so every field has a zero default. A data struct is one with a field tagged json, pg,
// env, yaml, db or bun. Structs that hold dependencies (clients, loggers) have no such tags and are
// skipped. A field may opt out with a trailing comment: //structcheck:allow <reason>.
//
//	go run ./scripts/structcheck <dir> [<dir>...]   exit 0 = clean, 1 = findings
package main

import (
	"fmt"
	"go/ast"
	"go/parser"
	"go/token"
	"io/fs"
	"os"
	"path/filepath"
	"reflect"
	"strings"
)

var dataTags = []string{"json", "pg", "env", "yaml", "db", "bun"}

// Finding is one rule violation at a source position.
type Finding struct {
	Pos     token.Position
	Message string
}

func main() {
	if len(os.Args) < 2 {
		fmt.Fprintln(os.Stderr, "usage: structcheck <dir> [<dir>...]")
		os.Exit(2)
	}
	var findings []Finding
	for _, dir := range os.Args[1:] {
		found, err := CheckDir(dir)
		if err != nil {
			fmt.Fprintln(os.Stderr, "structcheck:", err)
			os.Exit(2)
		}
		findings = append(findings, found...)
	}
	for _, f := range findings {
		fmt.Printf("%s: %s\n", f.Pos, f.Message)
	}
	if len(findings) > 0 {
		os.Exit(1)
	}
}

// CheckDir checks every non-test .go file under dir, skipping vendor and testdata.
func CheckDir(dir string) ([]Finding, error) {
	var findings []Finding
	fset := token.NewFileSet()
	err := filepath.WalkDir(dir, func(path string, d fs.DirEntry, err error) error {
		if err != nil {
			return err
		}
		if d.IsDir() {
			name := d.Name()
			if name == "vendor" || name == "testdata" || strings.HasPrefix(name, ".") && path != dir {
				return filepath.SkipDir
			}
			return nil
		}
		if !strings.HasSuffix(path, ".go") || strings.HasSuffix(path, "_test.go") {
			return nil
		}
		file, err := parser.ParseFile(fset, path, nil, parser.ParseComments)
		if err != nil {
			return err
		}
		findings = append(findings, CheckFile(fset, file)...)
		return nil
	})
	return findings, err
}

// CheckFile returns the findings for every data struct in one parsed file.
func CheckFile(fset *token.FileSet, file *ast.File) []Finding {
	var findings []Finding
	ast.Inspect(file, func(node ast.Node) bool {
		spec, ok := node.(*ast.TypeSpec)
		if !ok {
			return true
		}
		st, ok := spec.Type.(*ast.StructType)
		if !ok || !isDataStruct(st) {
			return true
		}
		for _, field := range st.Fields.List {
			if allowed(field) {
				continue
			}
			names := fieldNames(field)
			if isPointer(field.Type) {
				findings = append(findings, Finding{
					Pos:     fset.Position(field.Pos()),
					Message: fmt.Sprintf("%s.%s is a pointer; use a value field with a zero default (go-code: structs)", spec.Name.Name, names),
				})
			}
			if tag := tagValue(field); strings.Contains(tag, "omitempty") {
				findings = append(findings, Finding{
					Pos:     fset.Position(field.Pos()),
					Message: fmt.Sprintf("%s.%s uses omitempty; every field is always present (go-code: structs)", spec.Name.Name, names),
				})
			}
		}
		return true
	})
	return findings
}

func isDataStruct(st *ast.StructType) bool {
	for _, field := range st.Fields.List {
		tag := reflect.StructTag(tagValue(field))
		for _, key := range dataTags {
			if _, ok := tag.Lookup(key); ok {
				return true
			}
		}
	}
	return false
}

func tagValue(field *ast.Field) string {
	if field.Tag == nil {
		return ""
	}
	return strings.Trim(field.Tag.Value, "`")
}

func isPointer(expr ast.Expr) bool {
	switch t := expr.(type) {
	case *ast.StarExpr:
		return true
	case *ast.ArrayType:
		return isPointer(t.Elt)
	case *ast.MapType:
		return isPointer(t.Value)
	}
	return false
}

// allowed reports a trailing //structcheck:allow <reason> comment. CommentGroup.Text drops
// directive-style comments, so read the raw text; a reason is required.
func allowed(field *ast.Field) bool {
	if field.Comment == nil {
		return false
	}
	for _, c := range field.Comment.List {
		_, reason, found := strings.Cut(c.Text, "structcheck:allow")
		if found && strings.TrimSpace(reason) != "" {
			return true
		}
	}
	return false
}

func fieldNames(field *ast.Field) string {
	if len(field.Names) == 0 {
		return "(embedded)"
	}
	names := make([]string, len(field.Names))
	for i, name := range field.Names {
		names[i] = name.Name
	}
	return strings.Join(names, ",")
}
