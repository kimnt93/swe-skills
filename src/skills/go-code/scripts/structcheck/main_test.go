package main

import (
	"go/parser"
	"go/token"
	"strings"
	"testing"
)

func check(t *testing.T, src string) []Finding {
	t.Helper()
	fset := token.NewFileSet()
	file, err := parser.ParseFile(fset, "x.go", "package x\n"+src, parser.ParseComments)
	if err != nil {
		t.Fatal(err)
	}
	return CheckFile(fset, file)
}

func TestFlagsPointerAndOmitemptyInDataStructs(t *testing.T) {
	findings := check(t, "type Order struct {\n"+
		"\tID string `json:\"id\"`\n"+
		"\tPrice *float64 `json:\"price\"`\n"+
		"\tNote string `json:\"note,omitempty\"`\n"+
		"\tTags []*string `pg:\"tags\"`\n"+
		"}\n")
	if len(findings) != 3 {
		t.Fatalf("want 3 findings (pointer, omitempty, slice of pointers), got %d: %v", len(findings), findings)
	}
	if !strings.Contains(findings[0].Message, "Order.Price is a pointer") {
		t.Errorf("first finding: %s", findings[0].Message)
	}
}

func TestSkipsDependencyStructs(t *testing.T) {
	findings := check(t, "type Store struct {\n\tdb *DB\n\tlog *Logger\n}\n")
	if len(findings) != 0 {
		t.Fatalf("a struct with no data tags must be skipped, got %v", findings)
	}
}

func TestAllowCommentNeedsAReason(t *testing.T) {
	ok := check(t, "type Row struct {\n\tA *int `json:\"a\"` //structcheck:allow nullable column owned by another team\n}\n")
	if len(ok) != 0 {
		t.Fatalf("allow with a reason must pass, got %v", ok)
	}
	bare := check(t, "type Row struct {\n\tA *int `json:\"a\"` //structcheck:allow\n}\n")
	if len(bare) != 1 {
		t.Fatalf("allow without a reason must still fail, got %v", bare)
	}
}

func TestCleanValueStruct(t *testing.T) {
	findings := check(t, "type Config struct {\n\tPort int `env:\"PORT\"`\n\tHosts []string `env:\"HOSTS\"`\n}\n")
	if len(findings) != 0 {
		t.Fatalf("value fields must pass, got %v", findings)
	}
}
