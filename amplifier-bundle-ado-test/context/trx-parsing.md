# TRX Parsing

## TRX File Structure

Visual Studio Test Results XML format:

```xml
<?xml version="1.0" encoding="utf-8"?>
<TestRun>
  <Results>
    <UnitTestResult testId="..." testName="TestClassName.TestMethodName" 
                    outcome="Passed|Failed|Skipped" duration="00:00:00.123">
      <Output>
        <ErrorInfo>
          <Message>Assertion failed...</Message>
          <StackTrace>at ...</StackTrace>
        </ErrorInfo>
      </Output>
    </UnitTestResult>
  </Results>
  <ResultSummary outcome="Failed">
    <Counters total="100" passed="98" failed="2" />
  </ResultSummary>
</TestRun>
```

## Parsing Logic

```python
import xml.etree.ElementTree as ET

def parse_trx(trx_path):
    tree = ET.parse(trx_path)
    root = tree.getroot()
    
    # Handle namespace
    ns = {'t': 'http://microsoft.com/schemas/VisualStudio/TeamTest/2010'}
    
    results = []
    for result in root.findall('.//t:UnitTestResult', ns):
        error_node = result.find('.//t:Message', ns)
        results.append({
            'name': result.get('testName'),
            'outcome': result.get('outcome'),
            'duration': result.get('duration'),
            'error': error_node.text if error_node is not None else None
        })
    
    summary = root.find('.//t:Counters', ns)
    return {
        'total': int(summary.get('total')),
        'passed': int(summary.get('passed')),
        'failed': int(summary.get('failed')),
        'results': results
    }
```

## Summary Format

```
## Test Results
- **Total:** 100
- **Passed:** 98 ✓
- **Failed:** 2 ✗
- **Duration:** 45.2s

## Failures
1. `MyService.Tests.AuthTests.TokenRefresh_Expired_ShouldRefresh`
   > Expected: 200, Actual: 401
   
2. `MyService.Tests.ApiTests.RateLimit_Exceeded_ShouldReturn429`
   > System.TimeoutException: Operation timed out
```

## Flaky Detection

Track outcomes across last N runs:
- If test has >20% failure rate but <80% → flag as flaky
- Store history in `.amplifier/test-history.json` (gitignored)
