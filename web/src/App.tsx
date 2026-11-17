import { Route, Routes } from 'react-router-dom'
import Shell from './Shell'
import About from './pages/About'
import Buyer from './pages/Buyer'
import Home from './pages/Home'
import Market from './pages/Market'
import Supplier from './pages/Supplier'

export default function App() {
  return (
    <Shell>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/suppliers/:key" element={<Supplier />} />
        <Route path="/buyers/:key" element={<Buyer />} />
        <Route path="/markets/:cpv" element={<Market />} />
        <Route path="/about" element={<About />} />
        <Route path="*" element={<p className="py-24 text-center text-muted">Page not found.</p>} />
      </Routes>
    </Shell>
  )
}
