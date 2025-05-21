
import React from 'react';

function TestComponent(props) {
  const { name } = props;
  
  return (
    <div className="test-component">
      <h1>Hello, {name}!</h1>
      <p>This is a test React component.</p>
    </div>
  );
}

export default TestComponent;
                