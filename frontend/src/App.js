
import './App.css';
import { BrowserRouter as Router, Routes, Route, Link } from "react-router-dom";
import About from './About';
import Home from './Home';

function App() {
  return (
    <Router>
      <Routes>
          <Route exact path='/' element={< Home />}></Route>
				  <Route exact path='/about' element={< About />}></Route>
		    </Routes>
	  </Router>
  );
}

export default App;
